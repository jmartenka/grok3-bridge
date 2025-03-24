// Flag to track if we're waiting for a response
let pendingRequest = false;
let responseText = "";

// Debug function that sends messages to background script
function debug(level, message, data = null) {
	browser.runtime.sendMessage({
		type: 'debug',
		level: level,
		message: message,
		data: data
	});
}

// Function to extract cookies needed for Grok API
function getGrokCookies() {
	const relevantCookies = ['x-anonuserid', 'x-challenge', 'x-signature', 'sso', 'sso-rw'];
	const cookies = {};
	
	document.cookie.split(';').forEach(cookie => {
		const [name, value] = cookie.trim().split('=');
		if (relevantCookies.includes(name.toLowerCase())) {
			cookies[name] = value;
		}
	});
	
	debug('info', 'Extracted Grok cookies', cookies);
	return cookies;
}

// Function to send message to Grok API in the proper format
async function sendMessageToGrok(message) {
	debug('request', 'Sending message to Grok API', { message });
	
	const url = "https://grok.com/rest/app-chat/conversations/new";
	const cookies = getGrokCookies();
	
	const payload = {
		temporary: false,
		modelName: "grok-3",
		message: message,
		fileAttachments: [],
		imageAttachments: [],
		disableSearch: false,
		enableImageGeneration: true,
		returnImageBytes: false,
		returnRawGrokInXaiRequest: false,
		enableImageStreaming: true,
		imageGenerationCount: 2,
		forceConcise: false,
		toolOverrides: {},
		enableSideBySide: true,
		isPreset: false,
		sendFinalMetadata: true,
		customInstructions: "",
		deepsearchPreset: "",
		isReasoning: false
	};
	
	debug('info', 'Grok API request payload', payload);
	
	try {
		const startTime = performance.now();
		
		debug('info', 'Sending fetch request to Grok API', { url });
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Origin': 'https://grok.com',
				'Referer': 'https://grok.com/'
			},
			credentials: 'include',
			body: JSON.stringify(payload)
		});
		
		if (!response.ok) {
			const errorText = await response.text();
			debug('error', `HTTP error! Status: ${response.status}`, { 
				body: errorText, 
				headers: Object.fromEntries([...response.headers.entries()])
			});
			throw new Error(`HTTP error! Status: ${response.status}`);
		}

		debug('success', 'Received response from Grok API', { 
			status: response.status, 
			headers: Object.fromEntries([...response.headers.entries()]),
			timing: `${(performance.now() - startTime).toFixed(0)}ms`
		});
		
		// Handle streaming response
		const reader = response.body.getReader();
		responseText = "";
		let chunkCount = 0;
		
		debug('info', 'Starting to process response stream');
		
		// Process the stream
		while (true) {
			const { done, value } = await reader.read();
			if (done) {
				debug('info', 'Stream processing complete', { 
					totalChunks: chunkCount,
					totalLength: responseText.length
				});
				break;
			}
			
			// Convert the chunk to text
			const chunk = new TextDecoder().decode(value);
			chunkCount++;
			
			debug('info', `Processing chunk #${chunkCount}`, { 
				chunkSize: chunk.length,
				chunkPreview: chunk.substring(0, 100) + (chunk.length > 100 ? '...' : '')
			});
			
			const lines = chunk.split('\n');
			
			for (const line of lines) {
				if (!line.trim()) continue;
				
				try {
					const jsonData = JSON.parse(line);
					debug('info', 'Parsed JSON data', jsonData);
					
					const result = jsonData.result || {};
					const responseData = result.response || {};
					
					// Check if we have a complete response
					if (responseData.modelResponse) {
						responseText = responseData.modelResponse.message;
						debug('success', 'Received complete response from Grok', { 
							length: responseText.length,
							preview: responseText.substring(0, 100) + (responseText.length > 100 ? '...' : '')
						});
						break;
					}
					
					// Otherwise accumulate tokens
					const token = responseData.token || "";
					if (token) {
						responseText += token;
						debug('info', 'Added token to response', { 
							token,
							currentLength: responseText.length
						});
					}
				} catch (e) {
					debug('warning', 'Failed to parse JSON line', { 
						line: line.substring(0, 100) + (line.length > 100 ? '...' : ''),
						error: e.message
					});
					// Skip invalid JSON
					continue;
				}
			}
		}
		
		// Send the full response back to the background script
		if (responseText) {
			debug('response', 'Sending complete response to background script', { 
				length: responseText.length,
				preview: responseText.substring(0, 100) + (responseText.length > 100 ? '...' : '')
			});
			browser.runtime.sendMessage({ type: 'response', data: responseText });
		} else {
			debug('error', 'Empty response from Grok API');
			throw new Error('Empty response from Grok API');
		}
	} catch (error) {
		debug('error', 'Error sending message to Grok', {
			message: error.message,
			stack: error.stack
		});
		browser.runtime.sendMessage({ 
			type: 'response', 
			data: `Error communicating with Grok: ${error.message}` 
		});
	} finally {
		pendingRequest = false;
		debug('info', 'Request handling complete, ready for next request');
	}
}

// Listen for messages from the background script
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
	if (message.type === 'request') {
		const request = message.data;
		debug('request', 'Received request from background script', {
			request: request,
			sender: sender.id,
			pendingStatus: pendingRequest
		});
		
		// Don't process another request if we're still waiting for a response
		if (pendingRequest) {
			debug('warning', 'Ignoring request, still waiting for previous response');
			return;
		}
		
		pendingRequest = true;
		debug('info', 'Processing request', { request });
		sendMessageToGrok(request);
	}
});

// Log content script initialization
debug('info', 'Grok3 Bridge content script initialized', {
	url: window.location.href,
	timestamp: new Date().toISOString()
});
