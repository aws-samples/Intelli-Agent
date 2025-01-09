import React from 'react';

const UserMessage: React.FC = () => {
  return (
    <>
      <div className="messages">
        {[
          {
            id: 1,
            type: 'customer',
            text: 'Hello, I need help with my order',
            time: '14:30',
          },
          {
            id: 2,
            type: 'agent',
            text: "Hi! I'd be happy to help. Could you please provide your order number?",
            time: '14:31',
          },
          {
            id: 3,
            type: 'customer',
            text: "Sure, it's #12345",
            time: '14:32',
          },
          {
            id: 4,
            type: 'agent',
            text: 'Thank you! Let me check that for you...',
            time: '14:33',
          },
        ].map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-content">
              <p>{message.text}</p>
              <span className="time">{message.time}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input">
        <textarea placeholder="Type your message..." rows={3} />
        <button className="send-btn">
          <span className="icon">📤</span>
          Send
        </button>
      </div>
    </>
  );
};

export default UserMessage;
