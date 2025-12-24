import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Globe, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import axios from 'axios'
import SiteAnalyzer from './components/SiteAnalyzer'
import AnalysisResults from './components/AnalysisResults'
import LoadingSpinner from './components/LoadingSpinner'
import EmailCheck from './components/EmailCheck'
import PaymentForm from './components/PaymentForm'

function App() {
  const [email, setEmail] = useState('')
  const [sessionValid, setSessionValid] = useState(false)
  const [sessionInfo, setSessionInfo] = useState(null)
  const [showPayment, setShowPayment] = useState(false)
  const [url, setUrl] = useState('')
  const [occasion, setOccasion] = useState('') // Инфоповод для публикации
  const [isLoading, setIsLoading] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [error, setError] = useState(null)
  const [info, setInfo] = useState(null)
  const [lastAnalysis, setLastAnalysis] = useState(null) // Кэш последнего анализа
  const [usedStyles, setUsedStyles] = useState([]) // Использованные стили в текущей сессии
  const [availableStyles, setAvailableStyles] = useState(null) // Доступные стили из сеанса
  const [urlLocked, setUrlLocked] = useState(false) // URL заблокирован после первой генерации
  const [occasionLocked, setOccasionLocked] = useState(false) // Инфоповод заблокирован после первой генерации

  const backendUrl = 'http://localhost:8000'

  // Загружаем доступные стили при изменении сеанса
  useEffect(() => {
    if (sessionValid && email && sessionInfo?.available_styles) {
      setAvailableStyles(sessionInfo.available_styles)
      // Обновляем список использованных стилей
      const used = Object.entries(sessionInfo.available_styles)
        .filter(([_, value]) => value === 0)
        .map(([key, _]) => key)
      setUsedStyles(used)
    }
  }, [sessionValid, email, sessionInfo])

  // Загружаем URL и инфоповод из БД при валидном сеансе
  useEffect(() => {
    if (sessionValid && sessionInfo) {
      console.log('[DEBUG] Loading URL and INFO from sessionInfo:', {
        url: sessionInfo.url,
        info: sessionInfo.info,
        urlType: typeof sessionInfo.url,
        infoType: typeof sessionInfo.info
      })
      
      // Если URL есть в БД - загружаем и блокируем
      const urlValue = sessionInfo.url || ''
      if (urlValue.trim() !== '') {
        console.log('[DEBUG] Setting URL from DB:', urlValue)
        setUrl(urlValue)
        setUrlLocked(true)  // Блокируем, так как уже заполнено в БД
      } else {
        console.log('[DEBUG] URL is empty, allowing input')
        setUrl('')
        setUrlLocked(false)  // Разрешаем ввод, если пусто
      }
      
      // Если инфоповод есть в БД - загружаем и блокируем
      const infoValue = sessionInfo.info || ''
      if (infoValue.trim() !== '') {
        console.log('[DEBUG] Setting INFO from DB:', infoValue)
        setOccasion(infoValue)
        setOccasionLocked(true)  // Блокируем, так как уже заполнено в БД
      } else {
        console.log('[DEBUG] INFO is empty, allowing input')
        setOccasion('')
        setOccasionLocked(false)  // Разрешаем ввод, если пусто
      }
    }
    // Убрали лог для случая, когда сеанс еще не валиден - это нормально при первой загрузке
  }, [sessionValid, sessionInfo])

  // Проверяем, вернулись ли мы после оплаты (по URL параметрам)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('payment_success') === 'true') {
      // Очищаем URL параметры
      window.history.replaceState({}, document.title, window.location.pathname)
      // Показываем форму ввода email для нового входа
      setSessionValid(false)
      setShowPayment(false)
    }
  }, [])

  const checkSession = async (emailToCheck) => {
    try {
      const response = await axios.get(`${backendUrl}/session/check/${encodeURIComponent(emailToCheck)}`)
      const data = response.data
      if (data.has_session && data.is_active) {
        setSessionValid(true)
        setSessionInfo(data)
        setShowPayment(false)
      } else {
        setSessionValid(false)
        setShowPayment(true)
      }
    } catch (err) {
      setSessionValid(false)
      setShowPayment(true)
    }
  }

  const handleSessionValid = (emailValue, sessionData) => {
    console.log('[DEBUG] handleSessionValid called with:', {
      email: emailValue,
      sessionData: sessionData,
      url: sessionData?.url,
      info: sessionData?.info,
      urlType: typeof sessionData?.url,
      infoType: typeof sessionData?.info
    })
    setEmail(emailValue)
    setSessionValid(true)
    setSessionInfo(sessionData)
    setShowPayment(false)
    
    // Сразу загружаем URL и инфоповод из sessionData, если они есть
    // Это гарантирует, что данные будут установлены даже если useEffect не сработает
    if (sessionData) {
      const urlValue = sessionData.url || ''
      const infoValue = sessionData.info || ''
      
      console.log('[DEBUG] Directly setting URL and INFO from sessionData:', {
        urlValue,
        infoValue,
        urlLength: urlValue.length,
        infoLength: infoValue.length
      })
      
      if (urlValue.trim() !== '') {
        console.log('[DEBUG] Setting URL and locking:', urlValue)
        setUrl(urlValue)
        setUrlLocked(true)
      } else {
        console.log('[DEBUG] URL is empty, unlocking')
        setUrl('')
        setUrlLocked(false)
      }
      
      if (infoValue.trim() !== '') {
        console.log('[DEBUG] Setting INFO and locking:', infoValue)
        setOccasion(infoValue)
        setOccasionLocked(true)
      } else {
        console.log('[DEBUG] INFO is empty, unlocking')
        setOccasion('')
        setOccasionLocked(false)
      }
    }
    
    // НЕ сохраняем email в localStorage - каждый вход с чистого листа
  }

  const handlePaymentSuccess = async (emailValue) => {
    setEmail(emailValue)
    // НЕ сохраняем email в localStorage - каждый вход с чистого листа
    // Проверяем сеанс после успешной оплаты
    await checkSession(emailValue)
  }

  const handleAnalyze = async (siteUrl, style = 'убедительно-позитивном', occasionText = '') => {
    if (!sessionValid || !email) {
      setError('Необходимо проверить сеанс перед анализом')
      return
    }

    setIsLoading(true)
    setError(null)
    setInfo(null)
    setAnalysisData(null)
    
    // НЕ используем кэш - каждый запрос выполняется заново
    // Сбрасываем кэш последнего анализа
    setLastAnalysis(null)
    
    try {
      const response = await axios.post(`${backendUrl}/llm/analyze-site-sync`, {
        url: siteUrl,
        email: email,
        style: style,
        occasion: occasionText,
        use_cached: false,  // Всегда false - не используем кэш
        cached_intermediate: null  // Не передаем кэшированные данные
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 300000, // 5 минут таймаут
      })
      // Если бэкенд сообщил об усечении, выводим информационное сообщение
      if (response.data?.truncated && response.data?.truncation_message) {
        setInfo(response.data.truncation_message)
      }
      
      setAnalysisData(response.data)
      // НЕ сохраняем в кэш - каждый запрос выполняется заново
      
      // Блокируем URL и инфоповод после первой успешной генерации
      if (!urlLocked) {
        setUrlLocked(true)
      }
      if (!occasionLocked) {
        setOccasionLocked(true)
      }
      
      // Добавляем использованный стиль в список
      if (!usedStyles.includes(style)) {
        setUsedStyles([...usedStyles, style])
      }
      } catch (err) {
        console.error('API Error:', err)
        console.error('Error details:', {
          message: err.message,
          code: err.code,
          response: err.response?.data,
          status: err.response?.status,
          requestData: {
            url: siteUrl,
            email: email,
            style: style,
            occasion: occasionText
          }
        })
        // Выводим полную информацию об ошибке для отладки
        if (err.response?.data) {
          console.error('=== BACKEND ERROR RESPONSE ===')
          console.error(JSON.stringify(err.response.data, null, 2))
          console.error('Error detail field:', err.response.data?.detail)
          console.error('Error message field:', err.response.data?.message)
          if (Array.isArray(err.response.data?.detail)) {
            err.response.data.detail.forEach((error, index) => {
              console.error(`Validation error ${index + 1}:`, error)
            })
          }
          console.error('=== END BACKEND ERROR ===')
        } else {
          console.error('No response data in error!')
        }
      
      if (err.response) {
        // Обработка ошибок сеанса
        if (err.response.status === 403 || err.response.status === 410) {
          setSessionValid(false)
          setShowPayment(true)
          setError(err.response.data?.detail || 'Сеанс истек или не найден')
        } else if (err.response.status === 400) {
          // Обработка всех ошибок 400
          const errorDetail = err.response.data?.detail || err.response.data?.message || 'Неизвестная ошибка'
          if (errorDetail.includes('уже использован') || errorDetail.includes('недоступен')) {
            setError(errorDetail)
            // Обновляем список использованных стилей
            await checkSession(email)
          } else if (errorDetail.includes('слишком большой')) {
            setInfo(errorDetail)
          } else {
            // Показываем детали ошибки для отладки
            console.error('400 Bad Request details:', errorDetail)
            setError(`Ошибка запроса: ${errorDetail}`)
          }
        } else {
          setError(`Ошибка сервера: ${err.response.status} - ${err.response.data?.detail || err.response.statusText}`)
        }
      } else if (err.code === 'ECONNABORTED') {
        // Таймаут 60 секунд: показываем информсообщение вместо ошибки
        setInfo('Запрос занял более 60 секунд и был остановлен. Попробуйте более простой сайт или повторите позже.')
      } else if (err.request) {
        setError(`Не удалось подключиться к серверу. URL: ${backendUrl}. Проверьте, что бэкенд запущен на порту 8000.`)
      } else {
        setError(`Ошибка: ${err.message}`)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    // Очищаем все данные - каждый запрос выполняется заново
    setAnalysisData(null)
    setError(null)
    setInfo(null)
    setLastAnalysis(null)  // Очищаем кэш
    // URL и occasion остаются для удобства пользователя
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <motion.header 
        className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50"
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="max-w-4xl mx-auto px-4 py-6">
          <motion.div 
            className="flex items-center justify-center space-x-3"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Globe className="w-8 h-8 text-primary-600" />
            <h1 className="text-3xl md:text-4xl font-display font-bold text-gray-900">
              Генератор постов соцсети
            </h1>
          </motion.div>
          <motion.p 
            className="text-center text-gray-600 mt-2 text-lg"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            Получите варианты публикаций для любого веб-сайта
          </motion.p>
        </div>
      </motion.header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <AnimatePresence>
          {!sessionValid && !showPayment && (
            <motion.div
              key="email-check"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <EmailCheck 
                onSessionValid={handleSessionValid}
                onShowPayment={(emailValue) => {
                  console.log('[DEBUG App] onShowPayment called with email:', emailValue)
                  setEmail(emailValue)
                  setShowPayment(true)
                  console.log('[DEBUG App] showPayment set to true, email set to:', emailValue)
                }}
                backendUrl={backendUrl}
              />
            </motion.div>
          )}

          {showPayment && (
            <motion.div
              key="payment"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <PaymentForm 
                email={email || ''}
                onPaymentSuccess={handlePaymentSuccess}
                onCancel={() => {
                  setShowPayment(false)
                  setEmail('')
                }}
                backendUrl={backendUrl}
              />
            </motion.div>
          )}

          {sessionValid && !analysisData && !isLoading && (
            <motion.div
              key="analyzer"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <SiteAnalyzer 
                url={url}
                setUrl={setUrl}
                occasion={occasion}
                setOccasion={setOccasion}
                onAnalyze={handleAnalyze}
                error={error}
                info={info}
                urlLocked={urlLocked}
                occasionLocked={occasionLocked}
                usedStyles={usedStyles}
                availableStyles={availableStyles}
                email={email}
              />
            </motion.div>
          )}

          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              className="flex justify-center items-center min-h-[400px]"
            >
              <LoadingSpinner />
            </motion.div>
          )}

          {analysisData && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <AnalysisResults 
                data={analysisData}
                onReset={handleReset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

export default App
