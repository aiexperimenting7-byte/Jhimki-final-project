import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'

// Generate or retrieve session ID
const getSessionId = () => {
  let sessionId = localStorage.getItem('savi_session_id')
  if (!sessionId) {
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    localStorage.setItem('savi_session_id', sessionId)
  }
  return sessionId
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const sessionId = useRef(getSessionId())

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await axios.post('/api/chat', {
        message: input,
        history: messages,
        session_id: sessionId.current
      })

      const assistantMessage = { 
        role: 'assistant', 
        content: response.data.response,
        products: response.data.products || [],
        intent_data: response.data.intent_data
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.',
        products: []
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="chat-container">
        <div className="chat-header">
          <h1>🛍️ Savi Shopping Assistant</h1>
          <p className="header-subtitle">Find your perfect traditional Indian jewelry & accessories</p>
        </div>
        
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome to Savi! 👋</h2>
              <p>I'm here to help you discover beautiful traditional Indian products.</p>
              <div className="quick-suggestions">
                <p>Try asking:</p>
                <button onClick={() => setInput("Show me some sarees")} className="suggestion-chip">
                  "Show me some sarees"
                </button>
                <button onClick={() => setInput("Looking for a silk kurta")} className="suggestion-chip">
                  "Looking for a silk kurta"
                </button>
                <button onClick={() => setInput("Red jewelry under 5000")} className="suggestion-chip">
                  "Red jewelry under 5000"
                </button>
              </div>
            </div>
          )}
          
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
              
              {message.products && message.products.length > 0 && (
                <div className="products-grid">
                  {message.products.map((product, idx) => (
                    <div key={idx} className="product-card">
                      <div className="product-header">
                        <h3 className="product-name">{product.name}</h3>
                        <span className="product-badge">{product.category}</span>
                      </div>
                      
                      <div className="product-details">
                        {product.color && (
                          <div className="detail-item">
                            <span className="detail-label">Color:</span>
                            <span className="detail-value">{product.color}</span>
                          </div>
                        )}
                        {product.fabric && (
                          <div className="detail-item">
                            <span className="detail-label">Fabric:</span>
                            <span className="detail-value">{product.fabric}</span>
                          </div>
                        )}
                        {product.technique && (
                          <div className="detail-item">
                            <span className="detail-label">Technique:</span>
                            <span className="detail-value">{product.technique}</span>
                          </div>
                        )}
                        {product.pattern && (
                          <div className="detail-item">
                            <span className="detail-label">Pattern:</span>
                            <span className="detail-value">{product.pattern}</span>
                          </div>
                        )}
                      </div>
                      
                      {product.description && (
                        <p className="product-description">{product.description}</p>
                      )}
                      
                      <div className="product-footer">
                        <div className="price-container">
                          <span className="price">{product.price}</span>
                          <span className="stock-badge in-stock">
                            ✓ In Stock
                          </span>
                        </div>
                        {product.colors_available && (
                          <p className="colors-available">
                            Colors: {product.colors_available}
                          </p>
                        )}
                        <div className="product-actions">
                          <button 
                            className="action-btn primary"
                            onClick={() => setInput(`Tell me more about ${product.name}`)}
                          >
                            Learn More
                          </button>
                          <button 
                            className="action-btn secondary"
                            onClick={() => setInput(`Show me similar to ${product.name}`)}
                          >
                            Similar Items
                          </button>
                        </div>
                      </div>
                      
                      {product.score && (
                        <div className="similarity-score">
                          Match: {(product.score * 100).toFixed(0)}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="message assistant">
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        <form className="input-container" onSubmit={sendMessage}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What are you looking for today?"
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
