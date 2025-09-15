'use client'

import React, { useState, useRef, useEffect } from 'react'

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
      timestamp: new Date("2025-01-16T10:00:00")
    }
  ])
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

  const searchMenuRecommendations = async (query: string) => {
    try {
      const response = await fetch('/api/search-menu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      if (!response.ok) throw new Error('검색 실패')
      const data = await response.json()
      return data.recommendations || []
    } catch (error) {
      console.error('메뉴 검색 오류:', error)
      return []
    }
  }

  const getNaverMenuInfo = async (menuName: string) => {
    try {
      const response = await fetch('/api/naver-menu-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_name: menuName }),
      })
      if (!response.ok) throw new Error('메뉴 정보 조회 실패')
      const data = await response.json()
      return data
    } catch (error) {
      console.error('네이버 메뉴 정보 조회 오류:', error)
      return null
    }
  }

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
      let response = ''
      let menuInfo = null
      let paymentInfo = null
      let qrCode = null

      if (userMessage.includes('추천') || userMessage.includes('뭐가 맛있') || userMessage.includes('인기')) {
        const recommendations = await searchMenuRecommendations(userMessage)
        if (recommendations.length > 0) {
          response = `추천 메뉴를 찾아드렸습니다! 다음 메뉴들이 인기가 많아요:\n\n${recommendations.map((item: any, index: number) => `${index + 1}. ${item.name} - ${item.description}`).join('\n')}`
        } else {
          response = '죄송합니다. 현재 추천할 수 있는 메뉴 정보를 찾을 수 없습니다.'
        }
      }
      else if (userMessage.includes('설명') || userMessage.includes('어떤') || userMessage.includes('뭐야')) {
        const menuKeywords = ['김치찌개', '된장찌개', '불고기', '비빔밥', '냉면', '삼겹살', '갈비', '치킨', '피자', '파스타']
        const foundMenu = menuKeywords.find(menu => userMessage.includes(menu))
        
        if (foundMenu) {
          menuInfo = await getNaverMenuInfo(foundMenu)
          if (menuInfo && menuInfo.success) {
            response = `${foundMenu}에 대해 설명드릴게요!\n\n${menuInfo.description}\n\n가격: ${menuInfo.price || '문의 바랍니다'}\n평점: ${menuInfo.rating || 'N/A'}/5`
          } else {
            response = `${foundMenu}는 맛있는 한국 전통 요리입니다. 자세한 정보는 직원에게 문의해 주세요!`
          }
        } else {
          response = '어떤 메뉴에 대해 알고 싶으신가요? 구체적인 메뉴명을 말씀해 주시면 자세히 설명드릴게요!'
        }
      }
      else if (userMessage.includes('결제') || userMessage.includes('계산') || userMessage.includes('삼성페이')) {
        const orderNumber = `ORDER-${Date.now()}`
        const amount = 15000
        
        paymentInfo = await processSamsungPay(amount, orderNumber)
        if (paymentInfo && paymentInfo.success) {
          qrCode = await generateQRCode(orderNumber)
          response = `삼성페이 결제가 완료되었습니다!\n\n주문번호: ${orderNumber}\n결제금액: ${amount.toLocaleString()}원\n결제방법: 삼성페이\n\n아래 QR 코드로 주문을 확인하실 수 있습니다.`
        } else {
          response = '죄송합니다. 결제 처리 중 오류가 발생했습니다. 다시 시도해 주세요.'
        }
      }
      else {
        response = '네, 무엇을 도와드릴까요? 메뉴 추천, 설명, 또는 결제에 대해 궁금한 것이 있으시면 언제든 말씀해 주세요!'
      }

      const agentMessage: Message = {
        id: Date.now().toString(),
        content: response,
        sender: 'agent',
        timestamp: new Date(),
        menuInfo,
        paymentInfo,
        qrCode
      }

      setMessages(prev => [...prev, agentMessage])
    } catch (error) {
      console.error('응답 생성 오류:', error)
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
        setIsListening(false)
      }
      recognitionRef.current.onerror = () => setIsListening(false)
      recognitionRef.current.onend = () => setIsListening(false)

      recognitionRef.current.start()
    } else {
      alert('음성 인식을 지원하지 않는 브라우저입니다.')
    }
  }

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      setIsListening(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* 아이폰 16 상단 안전 영역 + 헤더 */}
      <div className="bg-white shadow-sm border-b border-gray-200 pt-safe-top">
        <div className="px-4 py-4">
          <div className="flex items-center justify-center space-x-3">
            <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm">🍽️</span>
            </div>
            <div className="text-center">
              <h1 className="text-lg font-bold text-gray-900">점원 Agent</h1>
              <p className="text-xs text-gray-500">말 걸면 다 해주는 똑똑한 점원</p>
            </div>
          </div>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-3 py-2 ${
                message.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
              }`}
            >
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
              
              {/* 메뉴 정보 카드 */}
              {message.menuInfo && (
                <div className="mt-2 p-3 bg-orange-50 rounded-xl border border-orange-200">
                  <h4 className="font-semibold text-orange-800 mb-1 text-sm">📋 메뉴 정보</h4>
                  <div className="text-xs text-gray-700 space-y-1">
                    <p><span className="font-medium">가격:</span> {message.menuInfo.price}</p>
                    <p><span className="font-medium">평점:</span> {message.menuInfo.rating}/5</p>
                  </div>
                </div>
              )}

              {/* 결제 정보 카드 */}
              {message.paymentInfo && (
                <div className="mt-2 p-3 bg-green-50 rounded-xl border border-green-200">
                  <h4 className="font-semibold text-green-800 mb-1 text-sm">💳 결제 완료</h4>
                  <div className="text-xs text-gray-700 space-y-1">
                    <p><span className="font-medium">주문번호:</span> {message.paymentInfo.order_number}</p>
                    <p><span className="font-medium">결제금액:</span> {message.paymentInfo.amount?.toLocaleString()}원</p>
                    <p><span className="font-medium">결제방법:</span> 삼성페이</p>
                  </div>
                </div>
              )}

              {/* QR 코드 */}
              {message.qrCode && (
                <div className="mt-2 p-3 bg-blue-50 rounded-xl border border-blue-200 text-center">
                  <h4 className="font-semibold text-blue-800 mb-2 text-sm">📱 주문 확인 QR</h4>
                  <div className="w-20 h-20 bg-white border border-blue-300 rounded-lg mx-auto flex items-center justify-center">
                    <span className="text-xs text-gray-500">QR</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">QR 코드를 스캔하여 주문을 확인하세요</p>
                </div>
              )}

              <p className="text-xs opacity-60 mt-1">
                {message.timestamp.toLocaleTimeString('ko-KR', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </p>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white rounded-2xl px-3 py-2 border border-gray-200 shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-gray-500">답변 생성 중...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 - 아이폰 16 하단 안전 영역 */}
      <div className="bg-white border-t border-gray-200 px-4 py-3 pb-safe-bottom">
        {/* 빠른 액션 버튼들 */}
        <div className="flex space-x-2 mb-3 overflow-x-auto">
          <button
            onClick={() => handleUserMessage('메뉴 추천해주세요')}
            className="flex-shrink-0 px-3 py-1.5 bg-orange-100 text-orange-700 rounded-full text-xs font-medium hover:bg-orange-200 transition-colors"
            disabled={isLoading}
          >
            🍽️ 메뉴 추천
          </button>
          <button
            onClick={() => handleUserMessage('인기 메뉴가 뭐예요?')}
            className="flex-shrink-0 px-3 py-1.5 bg-red-100 text-red-700 rounded-full text-xs font-medium hover:bg-red-200 transition-colors"
            disabled={isLoading}
          >
            🔥 인기 메뉴
          </button>
          <button
            onClick={() => handleUserMessage('삼성페이로 결제할게요')}
            className="flex-shrink-0 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium hover:bg-blue-200 transition-colors"
            disabled={isLoading}
          >
            💳 결제하기
          </button>
        </div>

        {/* 입력창과 버튼들 */}
        <div className="flex items-center space-x-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleUserMessage(inputText)}
              placeholder="메뉴에 대해 궁금한 것을 물어보세요..."
              className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-gray-50"
              disabled={isLoading}
            />
          </div>
          
          {/* 음성 인식 버튼 */}
          <button
            onClick={isListening ? stopListening : startListening}
            className={`p-2.5 rounded-full transition-all duration-200 ${
              isListening 
                ? 'bg-red-500 text-white scale-105' 
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
            disabled={isLoading}
          >
            <span className="text-sm">{isListening ? '🔴' : '🎤'}</span>
          </button>
          
          {/* 전송 버튼 */}
          <button
            onClick={() => handleUserMessage(inputText)}
            disabled={!inputText.trim() || isLoading}
            className="p-2.5 bg-orange-500 text-white rounded-full hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
