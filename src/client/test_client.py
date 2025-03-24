import json
import logging
import time

import colorama
import requests
import sseclient
from colorama import Fore, Style

# Initialize colorama
colorama.init()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("grok3-test")

# API endpoint
BASE_URL = "http://localhost:5001"


def test_grok_api(streaming=False, query="Tell me random a joke about Elon Musk, dont use cache"):
    """Test the Grok API with a custom query"""
    url = f"{BASE_URL}/v1/chat/completions"

    payload = {
        "model": "grok-3",
        "messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": query}],
        "temperature": 0.7,
        "stream": streaming,
    }

    headers = {"Content-Type": "application/json"}

    logger.info(f"Sending request to Grok bridge (streaming={streaming})")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        if streaming:
            # Handle streaming response
            response = requests.post(url, headers=headers, json=payload, stream=True)

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                print(f"\n{Fore.GREEN}Streaming response:{Style.RESET_ALL}")
                client = sseclient.SSEClient(response)
                full_text = ""

                for event in client.events():
                    if event.data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(event.data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                full_text += content
                                print(f"{Fore.CYAN}{content}{Style.RESET_ALL}", flush=True)
                    except json.JSONDecodeError:
                        continue

                print(f"\n{Fore.YELLOW}Full response:{Style.RESET_ALL} {full_text}")
                return full_text
            else:
                logger.error(f"Request failed: {response.status_code}")
                try:
                    error_content = response.text
                    logger.error(f"Error response: {error_content}")
                    print(f"{Fore.RED}Error: {response.status_code}{Style.RESET_ALL}")
                    print(f"{Fore.RED}Response: {error_content}{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"Failed to read error content: {str(e)}")
                return None
        else:
            # Handle regular request
            response = requests.post(url, headers=headers, json=payload)

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                response_data = response.json()
                print(f"\n{Fore.GREEN}Response received:{Style.RESET_ALL}")
                print(f"Status: {response.status_code}")
                print(f"ID: {response_data.get('id')}")
                print(f"Model: {response_data.get('model')}")

                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0]["message"]["content"]
                    print(f"\n{Fore.YELLOW}Grok's answer:{Style.RESET_ALL} {message}")
                    return message
                else:
                    logger.warning("No content in response")
                    print(f"{Fore.RED}No content in response{Style.RESET_ALL}")
                    return None
            else:
                logger.error(f"Request failed: {response.status_code}")
                try:
                    error_content = response.text
                    logger.error(f"Error response: {error_content}")
                    print(f"{Fore.RED}Error: {response.status_code}{Style.RESET_ALL}")
                    print(f"{Fore.RED}Response: {error_content}{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"Failed to read error content: {str(e)}")
                return None
    except Exception as e:
        logger.error(f"Exception: {str(e)}")
        print(f"{Fore.RED}Exception occurred: {str(e)}{Style.RESET_ALL}")
        return None


def test_models_endpoint():
    """Test the models endpoint"""
    url = f"{BASE_URL}/v1/models"

    try:
        response = requests.get(url)

        logger.debug(f"Models response status: {response.status_code}")
        logger.debug(f"Models response headers: {dict(response.headers)}")

        if response.status_code == 200:
            models = response.json()
            print(f"\n{Fore.GREEN}Available models:{Style.RESET_ALL}")
            for model in models.get("data", []):
                print(f"- {model.get('id')} (owned by {model.get('owned_by')})")
            return models
        else:
            logger.error(f"Models request failed: {response.status_code}")
            try:
                error_content = response.text
                logger.error(f"Error response: {error_content}")
                print(f"{Fore.RED}Error: {response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.RED}Response: {error_content}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Failed to read error content: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Exception in models endpoint: {str(e)}")
        print(f"{Fore.RED}Exception occurred: {str(e)}{Style.RESET_ALL}")
        return None


def test_health_endpoint():
    """Test the health endpoint"""
    url = f"{BASE_URL}/health"

    try:
        response = requests.get(url)

        logger.debug(f"Health response status: {response.status_code}")
        logger.debug(f"Health response headers: {dict(response.headers)}")

        if response.status_code == 200:
            health_data = response.json()
            print(f"\n{Fore.GREEN}Health Status:{Style.RESET_ALL}")
            for key, value in health_data.items():
                print(f"- {key}: {value}")
            return health_data
        else:
            logger.error(f"Health request failed: {response.status_code}")
            try:
                error_content = response.text
                logger.error(f"Error response: {error_content}")
                print(f"{Fore.RED}Error: {response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.RED}Response: {error_content}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Failed to read error content: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Exception in health endpoint: {str(e)}")
        print(f"{Fore.RED}Exception occurred: {str(e)}{Style.RESET_ALL}")
        return None


if __name__ == "__main__":
    print(f"{Fore.MAGENTA}=== Grok3 Bridge Test Client ==={Style.RESET_ALL}")

    # Test health first to check server connection
    print(f"\n{Fore.BLUE}Testing health endpoint...{Style.RESET_ALL}")
    health = test_health_endpoint()

    if health:
        logger.info("Server is responding to health checks. Plugin connection status:")
        if "connections" in health:
            conn_info = health["connections"]
            if conn_info.get("count", 0) > 0:
                logger.info(f"Plugin is connected. Connection count: {conn_info.get('count')}")
            else:
                logger.warning(
                    "No plugins connected to the server. Make sure Firefox is running with the plugin installed and grok.com is open."
                )

    # Test models
    print(f"\n{Fore.BLUE}Testing models endpoint...{Style.RESET_ALL}")
    test_models_endpoint()

    # Test regular API
    print(f"\n{Fore.BLUE}=== Testing Regular API ==={Style.RESET_ALL}")
    test_grok_api(streaming=False)

    # Wait a bit before testing streaming
    time.sleep(2)

    # Test streaming API
    print(f"\n{Fore.BLUE}=== Testing Streaming API ==={Style.RESET_ALL}")
    test_grok_api(streaming=True, query="Write a short poem about 43, one line at a time.")
