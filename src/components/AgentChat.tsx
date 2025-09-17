'use client'

import React, { useState, useRef, useEffect } from 'react'
import { generateSessionId } from '../lib/agent'

interface Message {
  id: string
  content: string
  sender: 'user' | 'agent'
  timestamp: Date
  menuInfo?: any
  paymentInfo?: any
  qrCode?: string
}

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: '안녕하세요! 저는 말 걸면 다 해주는 점원 Agent입니다. 메뉴에 대해 궁금한 것이 있으시면 언제든 말씀해 주세요! 🍽️',
      sender: 'agent',
      timestamp: new Date()
    }
  ])
  const [sessionId] = useState(() => generateSessionId())
  const [inputText, setInputText] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const processSamsungPay = async (amount: number, orderNumber: string) => {
    try {
      const response = await fetch('/api/samsung-pay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, order_number: orderNumber, payment_method: 'samsung_pay' }),
      })
      if (!response.ok) throw new Error('결제 처리 실패')
      const data = await response.json()
      return data
    } catch (error) {
      console.error('삼성페이 결제 오류:', error)
      return null
    }
  }

  const generateQRCode = async (orderNumber: string) => {
    try {
      const response = await fetch('/api/generate-qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_number: orderNumber }),
      })
      if (!response.ok) throw new Error('QR 코드 생성 실패')
      const data = await response.json()
      return data.qr_data
    } catch (error) {
      console.error('QR 코드 생성 오류:', error)
      return null
    }
  }

  const generateAgentResponse = async (userMessage: string) => {
    setIsLoading(true)
    
    try {
      // 백엔드 agent API 호출
      const agentRequest = {
        sessionId: sessionId,
        message: userMessage,
        store: "옥소반",
        selectedNames: [],
        profile: {
          ageGroup: "senior",
          allergies: [],
          diseases: [],
          prefers: [],
          dislikes: []
        }
      }

      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentRequest),
      })

      if (!response.ok) {
        throw new Error(`Agent API error: ${response.status}`)
      }

      const agentResponse = await response.json()
      
      // 응답에서 필요한 정보 추출
      let menuInfo = null
      let paymentInfo = null
      let qrCode = null

      // 결제 관련 액션이 필요한 경우
      if (agentResponse.stage === 'payment' || agentResponse.total_amount) {
        const orderNumber = `ORDER-${Date.now()}`
        const amount = agentResponse.total_amount || 15000
        
        paymentInfo = await processSamsungPay(amount, orderNumber)
        if (paymentInfo && paymentInfo.success) {
          qrCode = await generateQRCode(orderNumber)
        }
      }

      const agentMessage: Message = {
        id: Date.now().toString(),
        content: agentResponse.message || agentResponse.speak || '죄송합니다. 응답을 생성할 수 없습니다.',
        sender: 'agent',
        timestamp: new Date(),
        menuInfo,
        paymentInfo,
        qrCode
      }

      setMessages(prev => [...prev, agentMessage])
    } catch (error) {
      console.error('Agent API 호출 오류:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: '죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해 주세요.',
        sender: 'agent',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleUserMessage = async (message: string) => {
    if (!message.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')

    await generateAgentResponse(message)
  }

  const startListening = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = 'ko-KR'

      recognitionRef.current.onstart = () => setIsListening(true)

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript
        setInputText(transcript)
        handleUserMessage(transcript)
      }

      recognitionRef.current.onerror = (event: any) => {
        console.error('음성 인식 오류:', event.error)
        setIsListening(false)
      }

      recognitionRef.current.onend = () => setIsListening(false)

      recognitionRef.current.start()
    } else {
      alert('이 브라우저는 음성 인식을 지원하지 않습니다.')
    }
  }

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                message.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              
              {/* 결제 정보 표시 */}
              {message.paymentInfo && message.paymentInfo.success && (
                <div className="mt-2 p-2 bg-green-50 rounded border border-green-200">
                  <h4 className="font-semibold text-green-800">결제 완료</h4>
                  <p className="text-sm text-green-600">금액: {message.paymentInfo.amount?.toLocaleString()}원</p>
                  <p className="text-sm text-green-600">방법: {message.paymentInfo.provider}</p>
                </div>
              )}
              
              {/* QR 코드 표시 */}
              {message.qrCode && (
                <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200">
                  <h4 className="font-semibold text-blue-800">주문 확인 QR 코드</h4>
                  <p className="text-sm text-blue-600">주문번호: {message.qrCode.order_number}</p>
                  <p className="text-sm text-blue-600">만료시간: {new Date(message.qrCode.expires_at).toLocaleString()}</p>
                </div>
              )}
              
              <div className="text-xs opacity-70 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 p-3 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span>응답 생성 중...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleUserMessage(inputText)}
            placeholder="메시지를 입력하세요..."
            className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => handleUserMessage(inputText)}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            전송
          </button>
          <button
            onClick={isListening ? stopListening : startListening}
            disabled={isLoading}
            className={`px-4 py-2 rounded-lg ${
              isListening
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-green-500 hover:bg-green-600 text-white'
            } disabled:opacity-50`}
          >
            {isListening ? '🛑 중지' : '🎤 음성'}
          </button>
        </div>
      </div>
    </div>
  )
}
