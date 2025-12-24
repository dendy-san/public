import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { CreditCard, Loader2, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react'
import axios from 'axios'

const PaymentForm = ({ email, onPaymentSuccess, onCancel, backendUrl = 'http://localhost:8000' }) => {
  const [amount, setAmount] = useState(1000.0)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [confirmationUrl, setConfirmationUrl] = useState(null)
  const [paymentId, setPaymentId] = useState(null)
  const [isCheckingStatus, setIsCheckingStatus] = useState(false)
  const [paymentWindow, setPaymentWindow] = useState(null)

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
      setError('Ошибка при проверке статуса оплаты')
    }
  }

  // Обработчик сообщений от окна оплаты
  useEffect(() => {
    const handleMessage = (event) => {
      // Проверяем, что сообщение от нашего домена
      if (event.origin !== window.location.origin) {
        return
      }

      if (event.data && event.data.type === 'payment-success') {
        console.log('[PaymentForm] Received payment success message from payment window')
        // Закрываем окно оплаты, если оно еще открыто
        if (paymentWindow && !paymentWindow.closed) {
          paymentWindow.close()
        }
        // Проверяем статус платежа и обновляем состояние
        if (paymentId) {
          checkPaymentStatus(paymentId)
        }
      }
    }

    window.addEventListener('message', handleMessage)
    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [paymentId, paymentWindow, email, backendUrl, onPaymentSuccess])

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
          email: email.trim(),
          amount: amount
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

      // Открываем страницу оплаты в новом окне и сохраняем ссылку
      const newWindow = window.open(data.confirmation_url, '_blank', 'width=800,height=600')
      setPaymentWindow(newWindow)

      // Начинаем проверку статуса платежа
      startPaymentStatusCheck(data.payment_id)
    } catch (err) {
      console.error('Payment creation error:', err)
      setError(err.response?.data?.detail || 'Ошибка при создании платежа')
    } finally {
      setIsProcessing(false)
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
    <motion.div
      className="max-w-md mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <div className="card">
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
              value={amount}
              onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
              min="100"
              step="100"
              className="input-field"
              required
              disabled={isProcessing || isCheckingStatus}
            />
            <p className="mt-1 text-xs text-gray-500">
              Минимальная сумма: 100 ₽
            </p>
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
                  <h3 className="text-sm font-medium text-red-800">Ошибка</h3>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </motion.div>
          )}

          {confirmationUrl && (
            <motion.div
              className="bg-blue-50 border border-blue-200 rounded-lg p-4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <div className="flex items-start">
                <ExternalLink className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">Оплата создана</h3>
                  <p className="text-sm text-blue-700 mt-1">
                    Страница оплаты открыта в новом окне. После оплаты сеанс будет активирован автоматически.
                  </p>
                  {isCheckingStatus && (
                    <div className="mt-2 flex items-center text-xs text-blue-600">
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Ожидание оплаты...
                    </div>
                  )}
                  <div className="mt-2 space-y-2">
                    <a
                      href={confirmationUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 underline"
                    >
                      Открыть страницу оплаты <ExternalLink className="w-4 h-4 ml-1" />
                    </a>
                    <button
                      type="button"
                      onClick={() => {
                        if (paymentId) {
                          checkPaymentStatus(paymentId)
                        }
                      }}
                      disabled={isCheckingStatus}
                      className="block text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-50"
                    >
                      {isCheckingStatus ? (
                        <span className="flex items-center">
                          <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          Проверка оплаты...
                        </span>
                      ) : (
                        'Проверить статус оплаты'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          <div className="flex gap-3">
            {onCancel && (
              <motion.button
                type="button"
                onClick={onCancel}
                disabled={isProcessing || isCheckingStatus}
                className="btn-secondary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.2 }}
              >
                Отмена
              </motion.button>
            )}
            <motion.button
              type="submit"
              disabled={!isValidEmail(email) || amount < 100 || isProcessing || isCheckingStatus}
              className={`btn-primary ${onCancel ? 'flex-1' : 'w-full'} disabled:opacity-50 disabled:cursor-not-allowed`}
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
                    Оплатить {amount} ₽
                  </>
                )}
              </span>
            </motion.button>
          </div>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Что входит в оплату:</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <CheckCircle2 className="w-4 h-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
              <span>Доступ к генератору постов на 24 часа</span>
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
  )
}

export default PaymentForm

