import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Settings, History, Save, RefreshCw, AlertCircle, CheckCircle2, Eye, EyeOff } from 'lucide-react'

const API_URL = 'http://localhost:8000/admin'

function AdminPanel() {
  const [params, setParams] = useState({ W: '', Price: '', ShopID: '', Ykassa_API: '' })
  const [history, setHistory] = useState({ W: [], Price: [], yookassa: [] })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState({})
  const [selectedParam, setSelectedParam] = useState('W')
  const [message, setMessage] = useState({ type: '', text: '' })
  const [showApiKey, setShowApiKey] = useState(false)

  // Загрузка параметров
  const loadParams = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/params`)
      setParams({
        W: response.data.W || '',
        Price: response.data.Price || '',
        ShopID: response.data.ShopID || '',
        Ykassa_API: response.data.Ykassa_API || ''
      })
      setMessage({ type: 'success', text: 'Параметры загружены' })
    } catch (error) {
      console.error('Ошибка загрузки параметров:', error)
      setMessage({ type: 'error', text: 'Ошибка загрузки параметров' })
    } finally {
      setLoading(false)
    }
  }

  // Загрузка истории параметра
  const loadHistory = async (paramName) => {
    try {
      const response = await axios.get(`${API_URL}/params/history/${paramName}?limit=50`)
      if (paramName === 'yookassa') {
        setHistory(prev => ({
          ...prev,
          yookassa: response.data.history || []
        }))
      } else {
        setHistory(prev => ({
          ...prev,
          [paramName]: response.data.history || []
        }))
      }
    } catch (error) {
      console.error(`Ошибка загрузки истории для ${paramName}:`, error)
    }
  }

  // Сохранение параметра W или Price
  const saveParam = async (paramName) => {
    if (!params[paramName]) {
      setMessage({ type: 'error', text: 'Значение не может быть пустым' })
      return
    }

    try {
      setSaving(prev => ({ ...prev, [paramName]: true }))
      setMessage({ type: '', text: '' })

      await axios.post(`${API_URL}/params/${paramName}`, {
        value: params[paramName]
      })

      setMessage({ type: 'success', text: `Параметр ${paramName} успешно сохранен` })
      await loadHistory(paramName)
      
      setTimeout(() => setMessage({ type: '', text: '' }), 3000)
    } catch (error) {
      console.error(`Ошибка сохранения ${paramName}:`, error)
      const errorMsg = error.response?.data?.detail || `Ошибка сохранения ${paramName}`
      setMessage({ type: 'error', text: errorMsg })
    } finally {
      setSaving(prev => ({ ...prev, [paramName]: false }))
    }
  }

  // Сохранение параметров ЮКассы (ShopID и Ykassa_API вместе)
  const saveYooKassaParams = async () => {
    if (!params.ShopID) {
      setMessage({ type: 'error', text: 'Shop ID не может быть пустым' })
      return
    }
    if (!params.Ykassa_API) {
      setMessage({ type: 'error', text: 'Ykassa API ключ не может быть пустым' })
      return
    }

    try {
      setSaving(prev => ({ ...prev, yookassa: true }))
      setMessage({ type: '', text: '' })

      await axios.post(`${API_URL}/params/yookassa`, {
        shop_id: params.ShopID,
        api_key: params.Ykassa_API
      })

      setMessage({ type: 'success', text: 'Параметры ЮКассы успешно сохранены' })
      await loadHistory('yookassa')
      
      setTimeout(() => setMessage({ type: '', text: '' }), 3000)
    } catch (error) {
      console.error('Ошибка сохранения параметров ЮКассы:', error)
      const errorMsg = error.response?.data?.detail || 'Ошибка сохранения параметров ЮКассы'
      setMessage({ type: 'error', text: errorMsg })
    } finally {
      setSaving(prev => ({ ...prev, yookassa: false }))
    }
  }

  // Загрузка при монтировании
  useEffect(() => {
    loadParams()
    loadHistory('W')
    loadHistory('Price')
    loadHistory('yookassa')
  }, [])

  // Загрузка истории при смене выбранного параметра
  useEffect(() => {
    if (selectedParam) {
      if (selectedParam === 'yookassa' && history.yookassa?.length === 0) {
        loadHistory('yookassa')
      } else if (selectedParam !== 'yookassa' && history[selectedParam]?.length === 0) {
        loadHistory(selectedParam)
      }
    }
  }, [selectedParam])

  const paramLabels = {
    W: 'W (длительность сеанса в минутах)',
    Price: 'Price (цена в рублях)',
    ShopID: 'Shop ID (код магазина ЮКассы)',
    Ykassa_API: 'Ykassa API (API ключ ЮКассы)'
  }

  // Функция для маскировки API ключа
  const maskApiKey = (key) => {
    if (!key) return ''
    if (key.length <= 4) return '•'.repeat(key.length)
    return '•'.repeat(key.length - 4) + key.slice(-4)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
            <Settings className="w-8 h-8 text-indigo-600" />
            Панель управления параметрами
          </h1>
          <p className="text-gray-600 mt-2">Управление системными параметрами и просмотр истории изменений</p>
        </div>

        {/* Сообщения */}
        {message.text && (
          <div className={`mb-4 p-4 rounded-lg flex items-center gap-3 ${
            message.type === 'error' 
              ? 'bg-red-50 text-red-800 border border-red-200' 
              : 'bg-green-50 text-green-800 border border-green-200'
          }`}>
            {message.type === 'error' ? (
              <AlertCircle className="w-5 h-5" />
            ) : (
              <CheckCircle2 className="w-5 h-5" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        {/* Основной контент в две колонки */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Левая колонка: Редактирование параметров */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <Settings className="w-5 h-5 text-indigo-600" />
                Редактирование параметров
              </h2>
              <button
                onClick={loadParams}
                disabled={loading}
                className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50"
                title="Обновить параметры"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="space-y-6">
              {/* Параметр W */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {paramLabels.W}
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={params.W}
                    onChange={(e) => setParams(prev => ({ ...prev, W: e.target.value }))}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Введите значение"
                    min="1"
                  />
                  <button
                    onClick={() => saveParam('W')}
                    disabled={saving.W || loading}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {saving.W ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Сохранение...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Сохранить
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Параметр Price */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {paramLabels.Price}
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={params.Price}
                    onChange={(e) => setParams(prev => ({ ...prev, Price: e.target.value }))}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Введите значение"
                    min="1"
                  />
                  <button
                    onClick={() => saveParam('Price')}
                    disabled={saving.Price || loading}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {saving.Price ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Сохранение...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Сохранить
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Параметры ЮКассы - Shop ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {paramLabels.ShopID}
                </label>
                <input
                  type="text"
                  value={params.ShopID}
                  onChange={(e) => setParams(prev => ({ ...prev, ShopID: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Введите Shop ID"
                />
              </div>

              {/* Параметры ЮКассы - Ykassa API */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {paramLabels.Ykassa_API}
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={params.Ykassa_API}
                    onChange={(e) => setParams(prev => ({ ...prev, Ykassa_API: e.target.value }))}
                    className="w-full px-4 py-2 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Введите API ключ"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition-colors"
                    title={showApiKey ? 'Скрыть ключ' : 'Показать ключ'}
                  >
                    {showApiKey ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Кнопка сохранения параметров ЮКассы */}
              <div>
                <button
                  onClick={saveYooKassaParams}
                  disabled={saving.yookassa || loading}
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {saving.yookassa ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Сохранение параметров ЮКассы...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Сохранить параметры ЮКассы
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Правая колонка: История изменений */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <History className="w-5 h-5 text-indigo-600" />
                История изменений
              </h2>
            </div>

            {/* Переключатель параметров */}
            <div className="mb-4 flex gap-2 border-b border-gray-200">
              <button
                onClick={() => setSelectedParam('W')}
                className={`px-4 py-2 font-medium transition-colors ${
                  selectedParam === 'W'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                W
              </button>
              <button
                onClick={() => setSelectedParam('Price')}
                className={`px-4 py-2 font-medium transition-colors ${
                  selectedParam === 'Price'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Price
              </button>
              <button
                onClick={() => setSelectedParam('yookassa')}
                className={`px-4 py-2 font-medium transition-colors ${
                  selectedParam === 'yookassa'
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                ЮКасса
              </button>
            </div>

            {/* Список истории */}
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {selectedParam === 'yookassa' ? (
                // История параметров ЮКассы
                history.yookassa && history.yookassa.length > 0 ? (
                  history.yookassa.map((entry, index) => (
                    <div
                      key={index}
                      className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="font-medium text-gray-800 mb-1">
                            Shop ID: <span className="text-indigo-600">{entry.shop_id}</span>
                          </div>
                          <div className="font-medium text-gray-800">
                            API Key: <span className="text-indigo-600 font-mono text-sm">{maskApiKey(entry.api_key)}</span>
                          </div>
                        </div>
                        <span className="text-xs text-gray-500 ml-4">
                          {new Date(entry.timestamp).toLocaleString('ru-RU')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        Источник: {entry.source === 'admin_panel' ? 'Админ-панель' : entry.source === 'initialized_from_env' ? 'Инициализация из .env' : entry.source}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>История изменений параметров ЮКассы пуста</p>
                    <p className="text-sm mt-1">Изменения появятся здесь после первого обновления параметров</p>
                  </div>
                )
              ) : (
                // История параметров W или Price
                history[selectedParam] && history[selectedParam].length > 0 ? (
                  history[selectedParam].map((entry, index) => (
                    <div
                      key={index}
                      className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium text-gray-800">
                          Значение: <span className="text-indigo-600">{entry.value}</span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(entry.timestamp).toLocaleString('ru-RU')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        Источник: {entry.source === 'admin_panel' ? 'Админ-панель' : entry.source === 'initialized_from_env' ? 'Инициализация из .env' : entry.source}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>История изменений пуста</p>
                    <p className="text-sm mt-1">Изменения появятся здесь после первого обновления параметра</p>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
