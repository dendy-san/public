import React, { useEffect, useState } from 'react'
import { Settings, Users, LogOut } from 'lucide-react'
import AdminPanel from './AdminPanel.jsx'
import LeadsPanel from './LeadsPanel.jsx'
import Login from './Login.jsx'
import { clearToken, getToken } from '../api.js'

const TABS = [
  { key: 'params', label: 'Параметры', icon: Settings },
  { key: 'leads', label: 'Лиды', icon: Users },
]

function App() {
  const [tab, setTab] = useState('params')
  // Токен может отсутствовать (не вводили) или оказаться просроченным —
  // тогда показываем экран входа.
  const [authorized, setAuthorized] = useState(() => Boolean(getToken()))

  // Любой ответ 401/503 из api.js сбрасывает токен и присылает это событие.
  useEffect(() => {
    const onUnauthorized = () => setAuthorized(false)
    window.addEventListener('admin-unauthorized', onUnauthorized)
    return () => window.removeEventListener('admin-unauthorized', onUnauthorized)
  }, [])

  if (!authorized) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Login onAuthorized={() => setAuthorized(true)} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Переключатель разделов. Общий заголовок и сообщения вынесены
            сюда, чтобы каждая панель отвечала только за своё содержимое. */}
        <div className="mb-6 flex items-end justify-between gap-2 border-b border-white/60">
          <div className="flex gap-2">
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-5 py-3 font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
                  tab === key
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-gray-600 hover:text-indigo-600 hover:bg-white/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {label}
              </button>
            ))}
          </div>

          <button
            onClick={() => {
              clearToken()
              setAuthorized(false)
            }}
            className="px-4 py-2 mb-1 text-sm text-gray-600 hover:text-indigo-700 flex items-center gap-2 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Выйти
          </button>
        </div>

        {tab === 'params' ? <AdminPanel /> : <LeadsPanel />}
      </div>
    </div>
  )
}

export default App
