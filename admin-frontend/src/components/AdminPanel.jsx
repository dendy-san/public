import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Settings, History, Save, RefreshCw, AlertCircle, CheckCircle2, KeyRound } from 'lucide-react'

const API_URL = 'http://localhost:8000/admin'

function AdminPanel() {
  // W, Price, ShopID — редактируемые значения.
  // apiKeyInput намеренно не заполняется значением с сервера: сервер
  // отдаёт только маску, а отправка маски обратно перезаписала бы реальный
  // ключ. Поэтому поле ключа остаётся пустым, пока админ не введёт новый.
  const [params, setParams] = useState({ W: '', Price: '', ShopID: '' })
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [hasApiKey, setHasApiKey] = useState(false)
  const [maskedApiKey, setMaskedApiKey] = useState('')

  const [history, setHistory] = useState({ W: [], Price: [], yookassa: [] })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedParam, setSelectedParam] = useState('W')
  const [message, setMessage] = useState({ type: '', text: '' })

  // Снимок загруженных значений, чтобы отправлять только реально изменённые поля
  const [initial, setInitial] = useState({ W: '', Price: '', ShopID: '' })

  // Загрузка параметров
  const loadParams = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/params`)
      const loaded = {
        W: response.data.W || '',
        Price: response.data.Price || '',
        ShopID: response.data.ShopID || ''
      }
      setParams(loaded)
      setInitial(loaded)
      setHasApiKey(Boolean(response.data.has_api_key))
      setMaskedApiKey(response.data.Ykassa_API || '')
      // Поле ввода ключа всегда остаётся пустым (см. комментарий выше)
      setApiKeyInput('')
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
        setHistory(prev => ({ ...prev, yookassa: response.data.history || [] }))
      } else {
        setHistory(prev => ({ ...prev, [paramName]: response.data.history || [] }))
      }
    } catch (error) {
      console.error(`Ошибка загрузки истории для ${paramName}:`, error)
    }
  }

  // Валидация W/Price: целое положительное число
  const isValidPositiveInt = (value) => {
    if (value === '' || value === null) return false
    const n = Number(value)
    return Number.isInteger(n) && n > 0
  }

  // Единственная кнопка сохранения: отправляем только изменённые поля
  const saveAll = async () => {
    setMessage({ type: '', text: '' })

    // Проверки до отправки
    if (params.W !== initial.W && !isValidPositiveInt(params.W)) {
      setMessage({ type: 'error', text: 'W должно быть целым положительным числом' })
      return
    }
    if (params.Price !== initial.Price && !isValidPositiveInt(params.Price)) {
      setMessage({ type: 'error', text: 'Price должно быть целым положительным числом' })
      return
    }

    const errors = []
    let savedAnything = false

    setSaving(true)
    try {
      // W
      if (params.W !== initial.W) {
        try {
          await axios.post(`${API_URL}/params/W`, { value: String(params.W) })
          savedAnything = true
        } catch (e) {
          errors.push(e.response?.data?.detail || 'Ошибка сохранения W')
        }
      }

      // Price
      if (params.Price !== initial.Price) {
        try {
          await axios.post(`${API_URL}/params/Price`, { value: String(params.Price) })
          savedAnything = true
        } catch (e) {
          errors.push(e.response?.data?.detail || 'Ошибка сохранения Price')
        }
      }

      // ЮKassa: отправляем, если изменился ShopID ИЛИ введён новый ключ.
      // Пустой api_key на сервере означает «оставить текущий ключ».
      const shopChanged = params.ShopID !== initial.ShopID
      const keyEntered = apiKeyInput.trim() !== ''
      if (shopChanged || keyEntered) {
        if (!params.ShopID.trim()) {
          errors.push('Shop ID не может быть пустым')
        } else {
          try {
            await axios.post(`${API_URL}/params/yookassa`, {
              shop_id: params.ShopID.trim(),
              api_key: keyEntered ? apiKeyInput.trim() : undefined
            })
            savedAnything = true
          } catch (e) {
            errors.push(e.response?.data?.detail || 'Ошибка сохранения параметров ЮКассы')
          }
        }
      }
    } finally {
      setSaving(false)
    }

    if (errors.length > 0) {
      setMessage({ type: 'error', text: errors.join('; ') })
      return
    }

    if (!savedAnything) {
      setMessage({ type: '', text: 'Нет изменений для сохранения' })
      return
    }

    setMessage({ type: 'success', text: 'Изменения сохранены' })
    // Перезагружаем значения и историю, чтобы снять изменённый флаг
    await loadParams()
    await Promise.all([loadHistory('W'), loadHistory('Price'), loadHistory('yookassa')])
    setTimeout(() => setMessage({ type: '', text: '' }), 4000)
  }

  // Загрузка при монтировании
  useEffect(() => {
    loadParams()
    loadHistory('W')
    loadHistory('Price')
    loadHistory('yookassa')
  }, [])

  const paramLabels = {
    W: 'W (длительность сеанса в минутах)',
    Price: 'Price (цена в рублях)',
    ShopID: 'Shop ID (код магазина ЮКассы)',
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
                <input
                  type="number"
                  value={params.W}
                  onChange={(e) => setParams(prev => ({ ...prev, W: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Введите значение"
                  min="1"
                />
              </div>

              {/* Параметр Price */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {paramLabels.Price}
                </label>
                <input
                  type="number"
                  value={params.Price}
                  onChange={(e) => setParams(prev => ({ ...prev, Price: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Введите значение"
                  min="1"
                />
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

              {/* Параметры ЮКассы - API ключ (реальный ключ с сервера не приходит) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Ykassa API (API ключ ЮКассы)
                </label>
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder={hasApiKey ? `Сохранён ключ ${maskedApiKey} — введите новый, чтобы заменить` : 'Введите API ключ'}
                  autoComplete="off"
                />
                <p className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                  <KeyRound className="w-3 h-3" />
                  {hasApiKey
                    ? 'Ключ сохранён и скрыт. Оставьте поле пустым, чтобы не менять его.'
                    : 'Ключ не задан. Введите его, чтобы включить оплату.'}
                </p>
              </div>

              {/* Единственная кнопка сохранения */}
              <div className="pt-2">
                <button
                  onClick={saveAll}
                  disabled={saving || loading}
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Сохранение...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Сохранить изменения
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
              {['W', 'Price', 'yookassa'].map((key) => (
                <button
                  key={key}
                  onClick={() => setSelectedParam(key)}
                  className={`px-4 py-2 font-medium transition-colors ${
                    selectedParam === key
                      ? 'text-indigo-600 border-b-2 border-indigo-600'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  {key === 'yookassa' ? 'ЮКасса' : key}
                </button>
              ))}
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
                            API Key: <span className="text-indigo-600 font-mono text-sm">{entry.api_key}</span>
                          </div>
                        </div>
                        <span className="text-xs text-gray-500 ml-4">
                          {new Date(entry.timestamp).toLocaleString('ru-RU')}
                        </span>
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
