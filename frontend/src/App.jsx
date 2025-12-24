import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Globe, Loader2, AlertCircle, CheckCircle2, X } from 'lucide-react'
import axios from 'axios'
import SiteAnalyzer from './components/SiteAnalyzer'
import AnalysisResults from './components/AnalysisResults'
import LoadingSpinner from './components/LoadingSpinner'
import EmailCheck from './components/EmailCheck'
import PaymentForm from './components/PaymentForm'

function App() {
  const [email, setEmail] = useState('')
  const [sessionValid, setSessionValid] = useState(false) // Всегда начинаем с false
  const [sessionInfo, setSessionInfo] = useState(null)
  const [showPayment, setShowPayment] = useState(false) // Всегда начинаем с false
  const [url, setUrl] = useState('')
  const [occasion, setOccasion] = useState('') // Инфоповод для публикации
  const [isLoading, setIsLoading] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [error, setError] = useState(null)
  const [info, setInfo] = useState(null)
  // Кэш больше не используется на клиенте - только на сервере (Redis)
  const [usedStyles, setUsedStyles] = useState([]) // Использованные стили в текущей сессии
  const [availableStyles, setAvailableStyles] = useState(null) // Доступные стили из сеанса
  const [urlLocked, setUrlLocked] = useState(false) // URL заблокирован после первой генерации
  const [occasionLocked, setOccasionLocked] = useState(false) // Инфоповод заблокирован после первой генерации
  const [sessionEndModal, setSessionEndModal] = useState(null) // Модальное окно завершения сеанса (блоки 22/23)

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
      
      // ВАЖНО: Проверки стилей (блок 20) НЕ выполняются здесь!
      // Согласно блок-схеме: "Переход на блок 19 только после завершения блока 17 или при переходе на блок 18"
      // Проверки будут выполнены в handleReset (блок 18) или при следующем запросе генерации
    }
  }, [sessionValid, email, sessionInfo])

  // Проверяем только возврат после оплаты
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const savedEmail = localStorage.getItem('userEmail')
    
    if (urlParams.get('payment_success') === 'true' && savedEmail) {
      // Только в случае возврата после оплаты проверяем сеанс автоматически
      setEmail(savedEmail)
      setTimeout(() => {
        checkSession(savedEmail)
      }, 2000)
      // Очищаем URL параметры
      window.history.replaceState({}, document.title, window.location.pathname)
    } else {
      // Всегда начинаем с пустого экрана ввода email
      setSessionValid(false)
      setShowPayment(false)
      setEmail('')
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
        
        // БЛОК 12: ПРИСВОЕНИЕ ЗНАЧЕНИЙ управляющим переменным из полей записи БД
        // При восстановлении прерванного сеанса (блок 03 → блок 11 → блок 12)
        // ВСЕ управляющие переменные должны быть восстановлены из БД
        
        // Восстанавливаем URL из БД (если есть)
        if (data.url !== null && data.url !== undefined) {
          setUrl(data.url)
          // БЛОК 10+: Если URL уже сохранен в БД (не пустой), блокируем его
          if (data.url.trim() !== '') {
            setUrlLocked(true)
          } else {
            // URL пустой - разрешаем ввод (блок 08)
            setUrlLocked(false)
          }
        } else {
          // URL отсутствует в БД - разрешаем ввод (блок 08)
          setUrl('')
          setUrlLocked(false)
        }
        
        // Восстанавливаем INFO из БД (если есть)
        if (data.info !== null && data.info !== undefined) {
          setOccasion(data.info)
          // БЛОК 10+: Если INFO уже сохранен в БД (не пустой), блокируем его
          if (data.info.trim() !== '') {
            setOccasionLocked(true)
          } else {
            // INFO пустой - разрешаем ввод (блок 08)
            setOccasionLocked(false)
          }
        } else {
          // INFO отсутствует в БД - разрешаем ввод (блок 08)
          setOccasion('')
          setOccasionLocked(false)
        }
        
        // ВАЖНО: Проверки стилей (блок 20) НЕ выполняются здесь!
        // Согласно блок-схеме: "Переход на блок 19 только после завершения блока 17 или при переходе на блок 18"
        // Проверки будут выполнены в handleReset (блок 18) или при следующем запросе генерации
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
    setEmail(emailValue)
    localStorage.setItem('userEmail', emailValue)
    
    if (sessionData && sessionData.has_session && sessionData.is_active) {
      // Есть активный сеанс
      setSessionValid(true)
      setSessionInfo(sessionData)
      setShowPayment(false)
      
      // БЛОК 12: ПРИСВОЕНИЕ ЗНАЧЕНИЙ управляющим переменным из полей записи БД
      // При восстановлении прерванного сеанса (блок 03 → блок 11 → блок 12)
      // ВСЕ управляющие переменные должны быть восстановлены из БД
      
      // Восстанавливаем URL из БД (если есть)
      if (sessionData.url !== null && sessionData.url !== undefined) {
        setUrl(sessionData.url)
        // БЛОК 10+: Если URL уже сохранен в БД (не пустой), блокируем его
        if (sessionData.url.trim() !== '') {
          setUrlLocked(true)
        } else {
          // URL пустой - разрешаем ввод (блок 08)
          setUrlLocked(false)
        }
      } else {
        // URL отсутствует в БД - разрешаем ввод (блок 08)
        setUrl('')
        setUrlLocked(false)
      }
      
      // Восстанавливаем INFO из БД (если есть)
      if (sessionData.info !== null && sessionData.info !== undefined) {
        setOccasion(sessionData.info)
        // БЛОК 10+: Если INFO уже сохранен в БД (не пустой), блокируем его
        if (sessionData.info.trim() !== '') {
          setOccasionLocked(true)
        } else {
          // INFO пустой - разрешаем ввод (блок 08)
          setOccasionLocked(false)
        }
      } else {
        // INFO отсутствует в БД - разрешаем ввод (блок 08)
        setOccasion('')
        setOccasionLocked(false)
      }
    } else {
      // Нет сеанса - показываем форму оплаты
      setSessionValid(false)
      setSessionInfo(null)
      setShowPayment(true)
    }
  }

  const handlePaymentSuccess = async (emailValue) => {
    // БЛОК 01: После успешной оплаты начинаем с чистого листа, как новый пользователь
    setEmail(emailValue)
    localStorage.setItem('userEmail', emailValue)
    
    // Очищаем все данные предыдущего сеанса
    setUrl('')
    setOccasion('')
    setUrlLocked(false)
    setOccasionLocked(false)
    setUsedStyles([])
    setAvailableStyles(null)
    setAnalysisData(null)
    setError(null)
    setInfo(null)
    
    // Проверяем сеанс после успешной оплаты
    await checkSession(emailValue)
  }

  const handleAnalyze = async (siteUrl, style = 'убедительно-позитивном', occasionText = '') => {
    if (!sessionValid || !email) {
      setError('Необходимо проверить сеанс перед анализом')
      return
    }

    // БЛОК 19/20: Проверки выполняются при переходе на блок 18 (выбор нового стиля)
    // Проверяем сеанс перед генерацией (при выборе нового стиля)
    try {
      const checkResponse = await axios.get(`${backendUrl}/session/check/${encodeURIComponent(email)}`)
      const checkData = checkResponse.data
      
      if (!checkData.has_session || !checkData.is_active) {
        // БЛОК 22: Сеанс завершен по времени - показываем модальное окно
        setSessionEndModal({
          reason: 'time_expired',
          message: checkData.message || 'Время сеанса истекло. Сеанс завершен.'
        })
        
        setSessionValid(false)
        setSessionInfo(null)
        localStorage.removeItem('userEmail')
        setIsLoading(false)
        return
      }
      
      // БЛОК 20: ПРОВЕРКА СТИЛЕЙ (наличия неиспользованных стилей)
      // Неиспользованных стилей НЕТ → переход на блок 23
      if (checkData.has_unused_styles === false) {
        // БЛОК 23: СООБЩЕНИЕ об исчерпании стилей - модальное выпадающее окно с крестиком закрытия
        setSessionEndModal({
          reason: 'styles_exhausted',
          message: 'Все стили использованы. Сеанс завершен.'
        })
        
        setSessionValid(false)
        setSessionInfo(null)
        localStorage.removeItem('userEmail')
        setIsLoading(false)
        return
      }
    } catch (err) {
      console.error('Failed to check session:', err)
      // Продолжаем выполнение даже при ошибке проверки
    }

    setIsLoading(true)
    setError(null)
    setInfo(null)
    setAnalysisData(null)
    
    // Кэш управляется только на сервере (Redis)
    // Используем кэш только если:
    // 1. URL уже был установлен в сеансе (urlLocked = true после первой успешной генерации)
    // 2. URL не изменился (совпадает с текущим siteUrl)
    // 3. sessionInfo.url уже установлен (не первый анализ после оплаты)
    // ВАЖНО: Бэкенд сам определяет использование кэша на основе session.url из БД,
    // но мы передаем use_cached как подсказку для оптимизации
    const useCached = urlLocked && 
                      sessionInfo?.url && 
                      sessionInfo.url !== '' && 
                      sessionInfo.url === siteUrl
    
    try {
      const response = await axios.post(`${backendUrl}/llm/analyze-site-sync`, {
        url: siteUrl,
        email: email,
        style: style,
        occasion: occasionText,
        use_cached: useCached,
        cached_intermediate: null // Больше не передаем клиентский кэш
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
      
      // Показываем пользователю, что использовали кэш (быстрая генерация)
      if (response.data?.cached) {
        setInfo('✨ Использован кэш! Генерация выполнена быстро.')
      }
      
      // БЛОК 17: ВЫВОД ПУБЛИКАЦИЙ - устанавливаем результат генерации
      // Пользователь видит результат и может сохранить его
      setAnalysisData(response.data)
      
      // ВАЖНО: Проверки времени и стилей (блоки 19-20) НЕ выполняются здесь!
      // Согласно блок-схеме: "Переход на блок 19 только после завершения блока 17 или при переходе на блок 18"
      // Проверки будут выполнены при закрытии результатов (handleReset) или при следующем запросе генерации
      
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
      
      // Обновляем информацию о сеансе после успешного анализа
      await checkSession(email)
    } catch (err) {
      console.error('API Error:', err)
      console.error('Error details:', {
        message: err.message,
        code: err.code,
        response: err.response?.data,
        status: err.response?.status
      })
      
      if (err.response) {
        // Обработка ошибок сеанса
        if (err.response.status === 403 || err.response.status === 410) {
          setSessionValid(false)
          setShowPayment(true)
          setError(err.response.data?.detail || 'Сеанс истек или не найден')
        } else if (err.response.status === 400) {
          const detail = err.response.data?.detail || ''
          // Проверяем, связана ли ошибка с уже использованным стилем
          if (detail.includes('уже использован') || detail.includes('недоступен')) {
            // Обновляем список использованных стилей
            await checkSession(email)
            
            // Проверяем, все ли стили использованы
            try {
              const checkResponse = await axios.get(`${backendUrl}/session/check/${encodeURIComponent(email)}`)
              const checkData = checkResponse.data
              
              if (checkData.has_unused_styles === false) {
                // БЛОК 23: Все стили использованы - показываем модальное окно
                setSessionEndModal({
                  reason: 'styles_exhausted',
                  message: 'Все стили использованы. Сеанс завершен.'
                })
                
                setSessionValid(false)
                setSessionInfo(null)
                localStorage.removeItem('userEmail')
                setIsLoading(false)
                return
              }
            } catch (checkErr) {
              console.error('Failed to check session after style error:', checkErr)
            }
            
            // Если не все стили использованы, показываем ошибку о конкретном стиле
            setError(detail)
            setIsLoading(false)
            return // Прерываем выполнение, не показываем другие ошибки
          } else {
            // Другие ошибки 400
            setError(detail || 'Проверьте введенные данные.')
          }
        } else if (err.response.status === 422) {
          // Ошибка валидации - показываем детали
          const detail = err.response.data?.detail
          if (typeof detail === 'string') {
            setError(detail)
          } else if (Array.isArray(detail)) {
            setError(detail.map(d => d.msg || d).join(', '))
          } else {
            setError('Проверьте введенные данные')
          }
        } else if (err.response.data?.detail && err.response.data.detail.includes('слишком большой')) {
          setInfo(err.response.data.detail)
        } else {
          setError(`Сервер вернул ошибку: ${err.response.status} - ${err.response.data?.detail || err.response.statusText}`)
        }
      } else if (err.code === 'ECONNABORTED') {
        // Таймаут 60 секунд: показываем информсообщение вместо ошибки
        setInfo('Запрос занял более 60 секунд и был остановлен. Попробуйте более простой сайт или повторите позже.')
      } else if (err.request) {
        setError(`Не удалось подключиться к серверу. URL: ${backendUrl}. Проверьте, что бэкенд запущен на порту 8000.`)
      } else {
        setError(err.message)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = async () => {
    // БЛОК 18: ПОВТОР - переход на новую генерацию (если сеанс активен)
    // БЛОК 19/20: Проверки выполняются после завершения блока 17 или при переходе на блок 18
    setAnalysisData(null)
    setError(null)
    setInfo(null)
    
    // Выполняем проверки сеанса (блоки 19-20) после закрытия результатов (блок 18)
    if (email && sessionValid) {
      try {
        const response = await axios.get(`${backendUrl}/session/check/${encodeURIComponent(email)}`)
        const data = response.data
        
        if (!data.has_session || !data.is_active) {
          // БЛОК 22: Сеанс завершен по времени - показываем модальное окно
          setSessionEndModal({
            reason: 'time_expired',
            message: data.message || 'Время сеанса истекло. Сеанс завершен.'
          })
          
          setSessionValid(false)
          setSessionInfo(null)
          localStorage.removeItem('userEmail')
          return
        }
        
        // БЛОК 20: ПРОВЕРКА СТИЛЕЙ (наличия неиспользованных стилей)
        // Неиспользованных стилей НЕТ → переход на блок 23
        if (data.has_unused_styles === false) {
          // БЛОК 23: СООБЩЕНИЕ об исчерпании стилей - модальное выпадающее окно с крестиком закрытия
          setSessionEndModal({
            reason: 'styles_exhausted',
            message: 'Все стили использованы. Сеанс завершен.'
          })
          
          setSessionValid(false)
          setSessionInfo(null)
          localStorage.removeItem('userEmail')
          return
        }
      } catch (err) {
        console.error('Failed to check session:', err)
        // Продолжаем выполнение даже при ошибке проверки
      }
    }
  }

  const handleSessionEndModalClose = async () => {
    // БЛОК 24: УДАЛЕНИЕ КЛИЕНТСКОЙ ЗАПИСИ из базы (после закрытия модального окна)
    // Удаляем сеанс на бэкенде
    if (email) {
      try {
        await axios.delete(`${backendUrl}/session/delete/${encodeURIComponent(email)}`)
      } catch (err) {
        console.error('Failed to delete session:', err)
        // Продолжаем выполнение даже при ошибке удаления
      }
    }
    
    // БЛОК 06: ПЕРЕХОД К ОПЛАТЕ
    // Очищаем все данные перед переходом к оплате
    setSessionEndModal(null)
    setShowPayment(true)
    setSessionValid(false)
    setSessionInfo(null)
    setUrl('')
    setOccasion('')
    setUrlLocked(false)
    setOccasionLocked(false)
    setUsedStyles([])
    setAvailableStyles(null)
    setAnalysisData(null)
    setError(null)
    setInfo(null)
    // Email сохраняется в состоянии для оплаты
    localStorage.removeItem('userEmail')
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
        <AnimatePresence mode="wait">
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
                onClose={() => {
                  // БЛОК 06: В случае отказа переход на блок 01 (ВХОД С ПАРАМЕТРОМ E-mail)
                  // Очищаем все данные, как будто входит новый пользователь
                  setShowPayment(false)
                  setEmail('')
                  setSessionValid(false)
                  setSessionInfo(null)
                  setUrl('')
                  setOccasion('')
                  setUrlLocked(false)
                  setOccasionLocked(false)
                  setUsedStyles([])
                  setAvailableStyles(null)
                  setAnalysisData(null)
                  setError(null)
                  setInfo(null)
                  localStorage.removeItem('userEmail')
                }}
                backendUrl={backendUrl}
              />
            </motion.div>
          )}

          {sessionValid && !analysisData && !isLoading && !sessionEndModal && (
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

        {/* БЛОКИ 22/23: Модальное окно завершения сеанса */}
        {sessionEndModal && (
          <>
            <motion.div
              className="fixed inset-0 bg-black/50 z-[80]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={handleSessionEndModalClose}
            />
            <div className="fixed inset-0 z-[90] flex items-center justify-center p-4">
              <motion.div
                className="max-w-md w-full bg-white rounded-lg shadow-xl"
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="p-6 relative">
                  {/* Крестик закрытия */}
                  <button
                    onClick={handleSessionEndModalClose}
                    className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                    aria-label="Закрыть"
                  >
                    <X className="w-6 h-6" />
                  </button>
                  
                  <div className="text-center mb-4">
                    <AlertCircle className="w-16 h-16 text-orange-500 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      {sessionEndModal.reason === 'time_expired' 
                        ? 'Время сеанса истекло' 
                        : 'Все стили использованы'}
                    </h3>
                    <p className="text-gray-600">
                      {sessionEndModal.message}
                    </p>
                  </div>
                  
                  <div className="mt-6">
                    <motion.button
                      onClick={handleSessionEndModalClose}
                      className="w-full px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      Понятно
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App
