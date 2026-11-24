import React, { useState, useEffect } from 'react'
import { Save, Undo2, Clock, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import api from '../api.js'

// В dev — vite proxy (vite.config.js). VITE_API_URL переопределяет на другой
// домен; по умолчанию относительный путь, и nginx контейнера проксирует сам.

function AdminPanel() {
  // W, Price, ShopID — редактируемые значения.
  // apiKeyInput намеренно не заполняется значением с сервера: сервер
  // отдаёт только маску, а отправка маски обратно перезаписала бы реальный
  // ключ. Поэтому поле ключа остаётся пустым, пока админ не введёт новый.
  const [params, setParams] = useState({ W: '', Price: '', ShopID: '' })
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [hasApiKey, setHasApiKey] = useState(false)
  const [maskedApiKey, setMaskedApiKey] = useState('')

  // Снимки конфигурации — единый список истории (W + Price + ShopID + маска ключа).
  // Клик по снимку подставляет его значения в форму; применение — кнопкой «Сохранить».
  const [snapshots, setSnapshots] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedSnapshot, setSelectedSnapshot] = useState(null)
  const [message, setMessage] = useState({ type: '', text: '' })

  // Снимок загруженных значений, чтобы отправлять только реально изменённые поля
  const [initial, setInitial] = useState({ W: '', Price: '', ShopID: '' })

  // Загрузка текущих параметров
  const loadParams = async () => {
    try {
      setLoading(true)
      const response = await api.get('/params')
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
      setSelectedSnapshot(null)
      setMessage({ type: 'success', text: 'Параметры загружены' })
    } catch (error) {
      console.error('Ошибка загрузки параметров:', error)
      setMessage({ type: 'error', text: 'Ошибка загрузки параметров' })
    } finally {
      setLoading(false)
    }
  }

  // Загрузка истории снимков конфигурации
  const loadSnapshots = async () => {
    try {
      const response = await api.get('/params/history/snapshot?limit=50')
      setSnapshots(response.data.history || [])
    } catch (error) {
      console.error('Ошибка загрузки истории снимков:', error)
    }
  }

  // Валидация W/Price: целое положительное число
  const isValidPositiveInt = (value) => {
    if (value === '' || value === null) return false
    const n = Number(value)
    return Number.isInteger(n) && n > 0
  }

  // Подставить снимок в форму (без записи на сервер).
  // Реальный API-ключ восстановить из снимка нельзя (хранится только маска),
  // поэтому поле ключа остаётся пустым = текущий ключ не меняется.
  const applySnapshot = (snap, index) => {
    const next = {
      W: snap.W != null ? String(snap.W) : '',
      Price: snap.Price != null ? String(snap.Price) : '',
      ShopID: snap.shop_id || '',
    }
    setParams(next)
    setApiKeyInput('')
    setSelectedSnapshot(index)
    setMessage({
      type: 'success',
      text: 'Снимок подставлен в форму. Проверьте значения и нажмите «Сохранить изменения».',
    })
  }

  // Единственная кнопка сохранения: отправляем только изменённые поля,
  // затем фиксируем полный снимок конфигурации в истории.
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
          await api.post('/params/W', { value: String(params.W) })
          savedAnything = true
        } catch (e) {
          errors.push(e.response?.data?.detail || 'Ошибка сохранения W')
        }
      }

      // Price
      if (params.Price !== initial.Price) {
        try {
          await api.post('/params/Price', { value: String(params.Price) })
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
            await api.post('/params/yookassa', {
              shop_id: params.ShopID.trim(),
              api_key: keyEntered ? apiKeyInput.trim() : undefined
            })
            savedAnything = true
          } catch (e) {
            errors.push(e.response?.data?.detail || 'Ошибка сохранения параметров ЮКассы')
          }
        }
      }

      // Фиксируем полный снимок конфигурации (пресет для истории).
      if (savedAnything) {
        try {
          await api.post('/params/snapshot')
        } catch (e) {
          errors.push(e.response?.data?.detail || 'Ошибка сохранения снимка')
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
    // Перезагружаем значения и снимки, чтобы снять флаг изменений
    await loadParams()
    await loadSnapshots()
    setTimeout(() => setMessage({ type: '', text: '' }), 4000)
  }

  // Загрузка при монтировании
  useEffect(() => {
    loadParams()
    loadSnapshots()
  }, [])

  // Каркас страницы (min-h-screen, max-w-7xl, переключатель разделов)
  // находится в App.jsx — здесь только содержимое раздела «Параметры».
  return (
    <>
        {/* Заголовок */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
            <Settings className="w-8 h-8 text-indigo-600" />
            Панель управления параметрами
          </h1>
          <p className="text-gray-600 mt-2">Управление системными параметрами и история конфигураций</p>
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
              {/*
                Единственная стрелка: возвращает в форму значения, реально
                лежащие на сервере, то есть отменяет незаписанные правки.
                При открытии страницы и после сохранения данные и так
                актуальны, поэтому отдельная кнопка обновления истории не нужна.
              */}
              <button
                onClick={loadParams}
                disabled={loading}
                className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50"
                title="Отменить правки: подставить значения, сохранённые на сервере"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="space-y-6">
              {/* Параметр W */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  W (длительность сеанса в минутах)
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
                  Price (цена в рублях)
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
                  Shop ID (код магазина ЮКассы)
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

          {/* Правая колонка: История конфигураций (снимки) */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <History className="w-5 h-5 text-indigo-600" />
                История изменений
              </h2>
            </div>

            <p className="text-sm text-gray-500 mb-4">
              Нажмите на конфигурацию, чтобы подставить её в форму, затем сохраните.
            </p>

            {/* Список снимков */}
            <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
              {snapshots.length > 0 ? (
                snapshots.map((entry, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => applySnapshot(entry, index)}
                    className={`w-full text-left p-4 border rounded-lg transition-colors ${
                      selectedSnapshot === index
                        ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-300'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-800 mb-1">
                          Shop ID: <span className="text-indigo-600">{entry.shop_id || '—'}</span>
                        </div>
                        <div className="font-medium text-gray-800">
                          API Key:
                          <span className="text-indigo-600 font-mono text-sm break-all">
                            {entry.api_key || '—'}
                          </span>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xs text-gray-500 mb-2">
                          {new Date(entry.timestamp).toLocaleString('ru-RU')}
                        </div>
                        <div className="flex items-center justify-end gap-3 text-gray-600">
                          <span>W</span>
                          <span className="font-bold text-gray-900 w-12 text-right">{entry.W ?? '—'}</span>
                        </div>
                        <div className="flex items-center justify-end gap-3 text-gray-600">
                          <span>Price</span>
                          <span className="font-bold text-gray-900 w-12 text-right">{entry.Price ?? '—'}</span>
                        </div>
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>История конфигураций пуста</p>
                  <p className="text-sm mt-1">Снимки появятся здесь после первого сохранения параметров</p>
                </div>
              )}
            </div>
          </div>
        </div>
    </>
  )
}

export default AdminPanel
