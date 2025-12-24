import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Mail, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import axios from 'axios'

const EmailCheck = ({ onSessionValid, backendUrl = 'http://localhost:8000' }) => {
  const [email, setEmail] = useState('')
  const [isChecking, setIsChecking] = useState(false)
  const [error, setError] = useState(null)
  const [sessionInfo, setSessionInfo] = useState(null)

  const handleCheck = async (e) => {
    e.preventDefault()
    if (!email.trim()) return

    setIsChecking(true)
    setError(null)
    setSessionInfo(null)

    try {
      const response = await axios.get(`${backendUrl}/session/check/${encodeURIComponent(email.trim())}`)
      const data = response.data

      if (data.has_session && data.is_active) {
        setSessionInfo(data)
        onSessionValid(email.trim(), data)
      } else {
        // Нет сеанса - сразу переходим к оплате
        if (onSessionValid) {
          onSessionValid(email.trim(), null)
        }
      }
    } catch (err) {
      console.error('Session check error:', err)
      if (err.response?.status === 404 || err.response?.status === 410) {
        // Нет сеанса - сразу переходим к оплате
        if (onSessionValid) {
          onSessionValid(email.trim(), null)
        }
      } else {
        setError(err.response?.data?.detail || 'Не удалось проверить сеанс')
      }
    } finally {
      setIsChecking(false)
    }
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
            <Mail className="w-8 h-8 text-primary-600" />
          </motion.div>
          <h2 className="text-2xl font-display font-semibold text-gray-900 mb-2">
            Введите ваш email
          </h2>
          <p className="text-gray-600">
            Для использования сервиса необходим активный сеанс
          </p>
        </div>

        <form onSubmit={handleCheck} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email адрес
            </label>
            <div className="relative">
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="input-field pr-10"
                required
                disabled={isChecking}
              />
              <Mail className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
            {email && !isValidEmail(email) && (
              <motion.p
                className="mt-2 text-sm text-red-600 flex items-center"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle className="w-4 h-4 mr-1" />
                Пожалуйста, введите корректный email
              </motion.p>
            )}
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

          {sessionInfo && (
            <motion.div
              className="bg-green-50 border border-green-200 rounded-lg p-4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <div className="flex items-start">
                <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">Сеанс активен</h3>
                  <p className="text-sm text-green-700 mt-1">{sessionInfo.message}</p>
                  {sessionInfo.available_styles && (
                    <div className="mt-2 text-xs text-green-600">
                      Доступно стилей: {Object.values(sessionInfo.available_styles).filter(v => v === 1).length}/9
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={!email.trim() || !isValidEmail(email) || isChecking}
            className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            transition={{ duration: 0.2 }}
          >
            <span className="flex items-center justify-center">
              {isChecking ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Проверка...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5 mr-2" />
                  Проверить сеанс
                </>
              )}
            </span>
          </motion.button>
        </form>
      </div>
    </motion.div>
  )
}

export default EmailCheck


