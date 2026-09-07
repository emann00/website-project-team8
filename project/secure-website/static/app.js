const text = new URLSearchParams(location.search).get("message");

if (message && text) {
    message.textContent = text;
}