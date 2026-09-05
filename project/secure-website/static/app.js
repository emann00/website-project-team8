const message = document.querySelector("#message");
const text = new URLSearchParams(location.search).get("message");

if (message && text) {
  message.innerHTML = text;
}
