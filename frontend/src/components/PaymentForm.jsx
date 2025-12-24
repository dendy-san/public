import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { CreditCard, Loader2, ExternalLink, CheckCircle2, AlertCircle, X } from 'lucide-react'
import axios from 'axios'

const PaymentForm = ({ email, onPaymentSuccess, onClose, backendUrl = 'http://localhost:8000' }) => {
  // Сумма не редактируется - берется из Redis на бэкенде
  const [price, setPrice] = useState(null) // Сумма из Redis (Price)
  const [durationMinutes, setDurationMinutes] = useState(null) // Продолжительность в минутах из Redis (W)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [confirmationUrl, setConfirmationUrl] = useState(null)
  const [paymentId, setPaymentId] = useState(null)
  const [isCheckingStatus, setIsCheckingStatus] = useState(false)

  // Конвертация минут в часы с округлением вверх
  const minutesToHours = (minutes) => {
    if (!minutes) return 24 // Значение по умолчанию
    return Math.ceil(minutes / 60)
  }

  // Получение правильной формы слова "час/часа/часов"
  const getHoursWord = (hours) => {
    const hoursStr = hours.toString()
    const lastDigit = parseInt(hoursStr[hoursStr.length - 1])
    const lastTwoDigits = hoursStr.length >= 2 ? parseInt(hoursStr.slice(-2)) : lastDigit
    
    // Правильное склонение: 1 час, 2-4 часа, 5-20 часов, 21 час, 22-24 часа, и т.д.
    if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
      return 'часов'
    } else if (lastDigit === 1) {
      return 'час'
    } else if (lastDigit >= 2 && lastDigit <= 4) {
      return 'часа'
    }
    return 'часов'
  }

  // Загружаем цену и продолжительность из Redis при монтировании компонента
  useEffect(() => {
    const fetchParams = async () => {
      try {
        // Загружаем цену и продолжительность (W) из одного эндпоинта
        const response = await axios.get(`${backendUrl}/payment/price`)
        setPrice(response.data.price)
        // Проверяем, есть ли duration_minutes в ответе (новый формат) или загружаем отдельно
        if (response.data.duration_minutes !== undefined) {
          console.log('Loaded W parameter:', response.data.duration_minutes, 'minutes')
          setDurationMinutes(response.data.duration_minutes)
        } else {
          // Fallback: загружаем отдельно из админ-эндпоинта
          try {
            const durationResponse = await axios.get(`${backendUrl}/admin/params/W`)
            console.log('Loaded W parameter from admin endpoint:', durationResponse.data.W)
            setDurationMinutes(durationResponse.data.W)
          } catch (durationErr) {
            console.error('Failed to fetch duration:', durationErr)
            setDurationMinutes(1440) // 24 часа по умолчанию
          }
        }
      } catch (err) {
        console.error('Failed to fetch params:', err)
        // Используем значения по умолчанию, если не удалось получить
        setPrice(1000)
        setDurationMinutes(1440) // 24 часа по умолчанию
      }
    }
    fetchParams()
  }, [backendUrl])

  const handlePayment = async (e) => {
    e.preventDefault()
    if (!email.trim()) return

    setIsProcessing(true)
    setError(null)
    setConfirmationUrl(null)

    try {
      const response = await axios.post(
        `${backendUrl}/payment/create`,
        {
          email: email.trim()
          // amount не передается - берется из .env на бэкенде
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000
        }
      )

      const data = response.data
      setConfirmationUrl(data.confirmation_url)
      setPaymentId(data.payment_id)

      // Открываем страницу оплаты в popup окне (модальном)
      // ЮКасса блокирует iframe через X-Frame-Options, поэтому используем popup
      // Параметры делают окно похожим на модальное: центрированное, определенного размера
      const width = 800
      const height = 900
      const left = (window.screen.width - width) / 2
      const top = (window.screen.height - height) / 2
      
      const paymentWindow = window.open(
        data.confirmation_url,
        'payment',
        `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes,toolbar=no,menubar=no,location=no,status=no`
      )
      
      // Начинаем проверку статуса платежа (без показа информационного сообщения)
      if (paymentWindow) {
        startPaymentStatusCheck(data.payment_id)
      }
    } catch (err) {
      console.error('Payment creation error:', err)
      setError(err.response?.data?.detail || 'Не удалось создать платеж')
    } finally {
      setIsProcessing(false)
    }
  }

  const checkPaymentStatus = async (paymentIdToCheck) => {
    setIsCheckingStatus(true)
    try {
      const response = await axios.get(`${backendUrl}/payment/status/${paymentIdToCheck}`)
      const data = response.data

      if (data.paid) {
        setIsCheckingStatus(false)
        onPaymentSuccess(email)
      } else {
        setIsCheckingStatus(false)
        setError('Оплата еще не подтверждена. Пожалуйста, дождитесь подтверждения или попробуйте позже.')
      }
    } catch (err) {
      console.error('Status check error:', err)
      setIsCheckingStatus(false)
      setError('Не удалось проверить статус оплаты')
    }
  }

  const startPaymentStatusCheck = (paymentId) => {
    setIsCheckingStatus(true)
    const checkInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${backendUrl}/payment/status/${paymentId}`)
        const data = response.data

        if (data.paid) {
          clearInterval(checkInterval)
          setIsCheckingStatus(false)
          onPaymentSuccess(email)
        }
      } catch (err) {
        console.error('Status check error:', err)
        // Продолжаем проверку
      }
    }, 3000) // Проверяем каждые 3 секунды

    // Останавливаем проверку через 5 минут
    setTimeout(() => {
      clearInterval(checkInterval)
      setIsCheckingStatus(false)
    }, 300000)
  }

  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  return (
    <>
      {/* Overlay */}
      <motion.div
        className="fixed inset-0 bg-black/50 z-40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => {}}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
    <motion.div
          className="max-w-md w-full"
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ duration: 0.3 }}
    >
          <div className="card relative max-h-[90vh] overflow-y-auto">
            {/* Кнопка закрытия */}
            {onClose && (
              <button
                onClick={onClose}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Закрыть"
              >
                <X className="w-6 h-6" />
              </button>
            )}
            
        <div className="text-center mb-6">
          <motion.div
            className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <CreditCard className="w-8 h-8 text-primary-600" />
          </motion.div>
          <h2 className="text-2xl font-display font-semibold text-gray-900 mb-2">
            Оплата доступа
          </h2>
          <p className="text-gray-600">
            Оплатите доступ к генератору постов
          </p>
        </div>

        <form onSubmit={handlePayment} className="space-y-4">
          <div>
            <label htmlFor="payment-email" className="block text-sm font-medium text-gray-700 mb-2">
              Email адрес
            </label>
            <input
              type="email"
              id="payment-email"
              value={email}
              readOnly
              className="input-field bg-gray-100 cursor-not-allowed"
            />
          </div>

              <div>
                <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
                  Сумма оплаты (₽)
                </label>
                <input
                  type="number"
                  id="amount"
                  value={price || ''}
                  readOnly
                  disabled
                  className="input-field bg-gray-100 cursor-not-allowed"
                  required
                />
              </div>

          {error && (
            <motion.div
              className="bg-red-50 border border-red-200 rounded-lg p-4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Блок "Оплата создана" убран - показываем только модальное окно оплаты */}

          <div className="space-y-3">
            <motion.button
              type="submit"
              disabled={!isValidEmail(email) || !price || isProcessing || isCheckingStatus}
              className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.2 }}
            >
              <span className="flex items-center justify-center">
                {isProcessing ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Создание платежа...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-5 h-5 mr-2" />
                    Оплатить {price || '...'} ₽
                  </>
                )}
              </span>
            </motion.button>
            
            {/* БЛОК 06: Кнопка отказа от оплаты - переход на блок 01 */}
            <motion.button
              type="button"
              onClick={() => {
                if (onClose) {
                  onClose()
                }
              }}
              className="w-full px-4 py-3 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.2 }}
            >
              Отказаться от оплаты
            </motion.button>
          </div>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Что входит в оплату:</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <CheckCircle2 className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
              <span>Доступ к генератору постов на {(() => {
                const hours = durationMinutes !== null ? minutesToHours(durationMinutes) : 24
                console.log('Display hours:', hours, 'from minutes:', durationMinutes)
                return `${hours} ${getHoursWord(hours)}`
              })()}</span>
            </li>
            <li className="flex items-start">
              <CheckCircle2 className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
              <span>9 различных стилей публикаций</span>
            </li>
            <li className="flex items-start">
              <CheckCircle2 className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
              <span>Генерация 3 постов для каждого стиля</span>
            </li>
            <li className="flex items-start">
              <CheckCircle2 className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
              <span>Экспорт результатов в DOCX</span>
            </li>
          </ul>
        </div>
      </div>
    </motion.div>
      </div>

      {/* Информационное сообщение убрано - popup окно открывается автоматически */}
    </>
  )
}

export default PaymentForm

