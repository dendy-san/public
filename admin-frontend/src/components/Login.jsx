import React, { useEffect, useState } from 'react'
import { Lock, Loader2, AlertCircle } from 'lucide-react'
import api, { setToken } from '../api.js'

/**
 * Экран ввода токена админ-панели.
 *
 * В dev-режиме ADMIN_TOKEN не задан и backend пускает без токена, поэтому
 * при загрузке проверяем это одним запросом и пускаем дальше без ввода.
 */
function Login({ onAuthorized }) {
  const [token, setTokenInput] = useState('')
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState(null)

  // Проверяем, нужен ли токен вообще (dev: ADMIN_TOKEN пуст → пущает).
  useEffect(() => {
    let cancelled = false
    api
      .get('/params')
      .then(() => {
        if (!cancelled) onAuthorized()
      })
      .catch((err) => {
        if (cancelled) return
        // 401 — токен нужен; 503 — ADMIN_TOKEN не настроен в prod.
        if (err.response?.status === 503) {
          setError('ADMIN_TOKEN не настроен на сервере. Доступ закрыт.')
        }
        setChecking(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    const value = token.trim()
    if (!value) return
    setToken(value)
    setError(null)
    // Проверяем токен до показа панелей, иначе пользователь увидит пустой
    // экран с ошибкой вместо понятного отказа на входе.
    api
      .get('/params')
      .then(() => onAuthorized())
      .catch((err) => {
        setTokenInput('')
        setError(
          err.response?.status === 401
            ? 'Неверный токен доступа.'
            : 'Не удалось подключиться к серверу.'
        )
      })
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="bg-white/90 backdrop-blur rounded-2xl shadow-xl p-8 w-full max-w-md"
      >
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mb-4">
            <Lock className="w-8 h-8 text-indigo-600" />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900">Админ-панель</h1>
          <p className="text-gray-600 text-sm mt-1 text-center">
            Доступ по токену: панель содержит персональные данные клиентов и
            реквизиты платежей.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        <label htmlFor="admin-token" className="block text-sm font-medium text-gray-700 mb-2">
          Токен доступа
        </label>
        <input
          id="admin-token"
          type="password"
          value={token}
          onChange={(e) => setTokenInput(e.target.value)}
          autoComplete="current-password"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          placeholder="ADMIN_TOKEN из .env"
        />

        <button
          type="submit"
          disabled={!token.trim()}
          className="mt-6 w-full px-4 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Войти
        </button>
      </form>
    </div>
  )
}

export default Login
