// Initialize Socket.IO with explicit options
const socket = io('http://localhost:5001', {
	transports: ['websocket', 'polling'],
	reconnection: true,
	reconnectionAttempts: 10,
	reconnectionDelay: 1000,
	timeout: 5000,
	forceNew: true,
	autoConnect: true
});

// Track connection state
let isConnected = false;
let useWebAccessibleResource = false;
let webResourceFrame = null;
let debugMode = true; // Set to true to enable debugging

// Debug function
function debug(type, message, data = null) {
	if (!debugMode) return;
	
	const styles = {
		info: 'background: #2196F3; color: white; padding: 2px 5px; border-radius: 3px;',
		success: 'background: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px;',
		error: 'background: #F44336; color: white; padding: 2px 5px; border-radius: 3px;',
		warning: 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;',
		request: 'background: #9C27B0; color: white; padding: 2px 5px; border-radius: 3px;',
		response: 'background: #009688; color: white; padding: 2px 5px; border-radius: 3px;'
	};
	
	const style = styles[type] || styles.info;
	
	if (data) {
		console.groupCollapsed(`%c GROK3-BRIDGE ${type.toUpperCase()} `, style, message);
		console.log(data);
		console.groupEnd();
	} else {
		console.log(`%c GROK3-BRIDGE ${type.toUpperCase()} `, style, message);
	}
}

// Socket.IO event handlers
socket.on('connect', () => {
	debug('success', 'Connected to Flask server');
	isConnected = true;
	useWebAccessibleResource = false;
});

socket.on('connect_error', (error) => {
	debug('error', 'Connection error:', error);
	isConnected = false;
	
	if (!useWebAccessibleResource && !webResourceFrame) {
		debug('info', 'Trying web accessible resource as fallback...');
		useWebAccessibleResource = true;
		setupWebResourceConnection();
	}
});

socket.on('disconnect', () => {
	debug('warning', 'Disconnected from Flask server');
	isConnected = false;
	
	setTimeout(() => {
		if (!isConnected && !useWebAccessibleResource) {
			debug('info', 'Attempting to reconnect...');
			socket.connect();
		}
	}, 2000);
});

socket.on('error', (error) => {
	debug('error', 'Socket error:', error);
});

socket.on('request', request => {
	debug('request', 'Received request from server', request);
	forwardRequestToContent(request);
});

// Set up the web accessible resource connection as a fallback
function setupWebResourceConnection() {
	webResourceFrame = document.createElement('iframe');
	webResourceFrame.src = browser.runtime.getURL('web_accessible_resources.html');
	webResourceFrame.style.display = 'none';
	document.body.appendChild(webResourceFrame);
	
	window.addEventListener('message', (event) => {
		if (event.data.type === 'connected') {
			debug('success', 'Connected via web accessible resource');
			isConnected = true;
			useWebAccessibleResource = true;
		} else if (event.data.type === 'error') {
			debug('error', 'Web resource connection error:', event.data.data);
		} else if (event.data.type === 'request') {
			debug('request', 'Received request via web resource', event.data.data);
			forwardRequestToContent(event.data.data);
		}
	});
}

// Forward request to content script
function forwardRequestToContent(request) {
	browser.tabs.query({ url: '*://grok.com/*' }, tabs => {
		if (tabs.length > 0) {
			debug('info', `Forwarding request to tab ${tabs[0].id}`, request);
			browser.tabs.sendMessage(tabs[0].id, { type: 'request', data: request });
		} else {
			debug('error', 'No Grok tabs found. Please open grok.com and log in.');
		}
	});
}

// Send response back to server
function sendResponseToServer(responseData) {
	debug('response', 'Sending response to server', responseData);
	
	if (useWebAccessibleResource && webResourceFrame) {
		webResourceFrame.contentWindow.postMessage({
			type: 'sendResponse',
			data: responseData
		}, '*');
	} else if (isConnected) {
		socket.emit('response', responseData);
	} else {
		debug('error', 'Not connected to server. Attempting to reconnect...');
		
		socket.connect();
		socket.once('connect', () => {
			socket.emit('response', responseData);
		});
	}
}

// Listen for messages from the content script
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
	if (message.type === 'response') {
		debug('info', 'Received response from content script', { 
			tabId: sender.tab.id,
			responseLength: message.data.length,
			preview: message.data.substring(0, 100) + (message.data.length > 100 ? '...' : '')
		});
		sendResponseToServer(message.data);
	} else if (message.type === 'debug') {
		debug(message.level || 'info', message.message, message.data);
	}
});

// Add a context menu item to toggle debugging
browser.contextMenus.create({
	id: 'toggleDebug',
	title: 'Toggle Grok3 Bridge Debugging',
	contexts: ['browser_action']
});

browser.contextMenus.onClicked.addListener((info, tab) => {
	if (info.menuItemId === 'toggleDebug') {
		debugMode = !debugMode;
		debug('info', `Debugging ${debugMode ? 'enabled' : 'disabled'}`);
	}
});

// Log startup
debug('info', 'Grok3 Bridge background script initialized', {
	version: '1.0',
	timestamp: new Date().toISOString()
});
