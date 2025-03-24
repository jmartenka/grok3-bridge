# Grok3 Bridge

**Because waiting for API access is so 2023...**

Look, we've all been there. Refreshing our emails daily, checking X/Twitter for announcements, sacrificing small electronic devices to the API gods... all while waiting for that sweet, sweet Grok 3 API access that never seems to arrive. Well, I got tired of waiting, so I built this unholy contraption instead!

## What Is This Madness?

This is a Firefox plugin + server combo that lets you talk to Grok 3 using the OpenAI API format. Yes, it's a hack. Yes, it works. No, I have no regrets.

It's basically three things:
- A Firefox plugin that sneakily talks to Grok's web interface
- A Flask server that pretends to be OpenAI
- Your ticket to using Grok 3 with whatever OpenAI-compatible tools you already have

## Project Structure

The project is organized as follows:
- `src/server/` - Contains the server code that bridges between clients and Grok
- `src/client/` - Contains test clients and examples
- `plugin/` - Contains the Firefox plugin that communicates with Grok

## Cool Features (Yes, It Actually Has Some)

- **Works with OpenAI clients**: No need to rewrite your code. Just point it at a different URL!
- **Direct Grok access**: All the goodness of Grok 3 without the waiting
- **Streaming support**: Watch the AI think in real-time, one token at a time
- **Python 3.13 compatible**: Because living on the bleeding edge is fun
- **Debugging tools**: Find out exactly what's happening when things inevitably break

## How This Contraption Works

1. You send a request to our fake OpenAI server
2. The server whispers it to the Firefox plugin via WebSockets
3. The plugin sweet-talks Grok's API directly
4. Grok answers (completely unaware of our shenanigans)
5. The response flows back through our digital Rube Goldberg machine
6. You get your answer formatted just like it came from OpenAI

## Getting This Thing Running

### Install the Firefox Plugin

1. Open Firefox and go to `about:debugging` (yes, type that in the address bar)
2. Click "This Firefox" (not the other Firefox, THIS Firefox)
3. Click "Load Temporary Add-on" (emphasis on "temporary" - it'll disappear when you close Firefox)
4. Find and select the `manifest.json` file in the `plugin` directory

### Fire Up the Server

```bash
# Got Poetry? If not:
# curl -sSL https://install.python-poetry.org | python3 -

# Install the dependencies
poetry install

# Let the magic begin
poetry run python src/server/server.py

# Or use the convenience script
./run_server.sh
```

### Log Into Grok

1. Visit [grok.com](https://grok.com) and log in
2. The plugin should connect automatically and you'll see "Plugin connected" in your terminal
3. If it doesn't connect, try dancing around your computer while chanting "API access please"

### Test This Contraption

```bash
# Run the test client
poetry run python src/client/test_client.py

# Or use the convenience script
./run_test.sh
```

This will check if everything's working by:
1. Poking the `/v1/models` endpoint
2. Sending a regular chat request
3. Trying out a streaming request (oooh fancy!)

## Using Your New "API"

Now you can use any OpenAI client by pointing it to `http://localhost:5000`:

### Python Example (OpenAI Client)

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:5000/v1",
    api_key="totally-fake-key-but-we-need-something-here"  # API key is ignored
)

# Ask something profound
response = client.chat.completions.create(
    model="grok-3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Why is waiting for API access so painful?"}
    ]
)
print(response.choices[0].message.content)

# Watch it think in real-time!
stream = client.chat.completions.create(
    model="grok-3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Count to 5 as if you're extremely excited about it."}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Node.js Example

```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'http://localhost:5000/v1',
  apiKey: 'this-could-literally-be-anything-just-like-how-a-viola-burns-longer-than-a-violin'
});

async function main() {
  const response = await openai.chat.completions.create({
    model: 'grok-3',
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'What is the capital of France? Wrong answers only.' }
    ]
  });
  
  console.log(response.choices[0].message.content);
}

main();
```

## Known Quirks and Features™

- **It's a hack**: Let's not pretend this is enterprise-grade software
- **Browser dependency**: You need to keep Firefox open with Grok logged in
- **No token counting**: All token counts are -1 because I don't want to count them and you can't make me
- **Debugging tools**: Check the browser console for colorful debug logs when things go sideways

## Disclaimer

This project was created because patience is a virtue I don't possess. Use it until x.ai gives you proper API access, then switch to that. Or don't. I'm not your boss.

May your wait for API access be shorter than mine was!