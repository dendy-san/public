import React, { useState } from 'react'
import { Settings, Users } from 'lucide-react'
import AdminPanel from './AdminPanel.jsx'
import LeadsPanel from './LeadsPanel.jsx'

const TABS = [
  { key: 'params', label: 'Параметры', icon: Settings },
  { key: 'leads', label: 'Лиды', icon: Users },
]

function App() {
  const [tab, setTab] = useState('params')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Переключатель разделов. Общий заголовок и сообщения вынесены
            сюда, чтобы каждая панель отвечала только за своё содержимое. */}
        <div className="mb-6 flex gap-2 border-b border-white/60">
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

        {tab === 'params' ? <AdminPanel /> : <LeadsPanel />}
      </div>
    </div>
  )
}

export default App
