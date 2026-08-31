import React, { useState } from "react";
import "./App.css";

function App() {
const [message, setMessage] = useState("");
const [history, setHistory] = useState([]);
const [messages, setMessages] = useState([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState("");

const sendMessage = async () => {
const userMessage = message.trim();


if (!userMessage || loading) {
  return;
}

setMessages((prev) => [
  ...prev,
  { role: "user", content: userMessage },
]);

setMessage("");
setLoading(true);
setError("");

try {
  const response = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: userMessage,
      history: history,
    }),
  });

  if (!response.ok) {
    throw new Error("Backend request failed");
  }

  const data = await response.json();

  setMessages((prev) => [
    ...prev,
    {
      role: "assistant",
      content: data.answer || "",
      sources: data.sources || [],
      handoff: data.handoff || false,
    },
  ]);

  setHistory((prev) => [
    ...prev,
    { role: "user", content: userMessage },
    { role: "assistant", content: data.answer || "" },
  ]);
} catch (err) {
  console.error(err);
  setError("Unable to connect to the support agent.");
} finally {
  setLoading(false);
}


};

const clearChat = () => {
setMessages([]);
setHistory([]);
setError("");
};

return ( <div className="app"> <header className="header"> <div> <h1>AI Support Agent</h1> <p>Aster & Row Customer Support</p> </div>

```
    <button
      type="button"
      className="clear-button"
      onClick={clearChat}
    >
      Clear Chat
    </button>
  </header>

  <main className="chat-container">
    {messages.length === 0 && (
      <div className="welcome">
        <h2>How can I help you?</h2>
        <p>
          Ask about returns, shipping, warranties, or your order.
        </p>
      </div>
    )}

    <div className="messages">
      {messages.map((msg, index) => (
        <div
          key={index}
          className={
            msg.role === "user"
              ? "message-row user-row"
              : "message-row agent-row"
          }
        >
          <div
            className={
              msg.role === "user"
                ? "message user-message"
                : "message agent-message"
            }
          >
            <div className="message-label">
              {msg.role === "user" ? "You" : "AI Support Agent"}
            </div>

            <div className="message-content">
              {msg.content}
            </div>

            {msg.sources && msg.sources.length > 0 && (
              <div className="sources">
                <strong>Sources</strong>

                {msg.sources.map((source, sourceIndex) => (
                  <div key={sourceIndex} className="source">
                    {source}
                  </div>
                ))}
              </div>
            )}

            {msg.handoff && (
              <div className="handoff">
                Human support required
              </div>
            )}
          </div>
        </div>
      ))}

      {loading && (
        <div className="message-row agent-row">
          <div className="message agent-message">
            <div className="message-label">
              AI Support Agent
            </div>

            <div className="typing">
              Thinking...
            </div>
          </div>
        </div>
      )}
    </div>

    {error && (
      <div className="error">
        {error}
      </div>
    )}

    <div className="input-area">
      <input
        type="text"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
          }
        }}
        placeholder="Ask a support question..."
        disabled={loading}
      />

      <button
        type="button"
        onClick={sendMessage}
        disabled={loading}
      >
        {loading ? "Sending..." : "Send"}
      </button>
    </div>
  </main>
</div>


);
}

export default App;
