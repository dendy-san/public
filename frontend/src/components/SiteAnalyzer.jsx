import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, AlertCircle, ExternalLink } from 'lucide-react'
import { STYLES, STYLE_VALUES, STYLE_COUNT, DEFAULT_STYLE } from './styles'

const SiteAnalyzer = ({ url, setUrl, occasion, setOccasion, onAnalyze, error, info, urlLocked = false, occasionLocked = false, usedStyles = [], availableStyles = null, email = '' }) => {
  const [style, setStyle] = useState(DEFAULT_STYLE)

  // Определяем доступные стили на основе сеанса
  const getAvailableStylesList = () => {
    if (availableStyles) {
      return Object.entries(availableStyles)
        .filter(([_, value]) => value === 1)
        .map(([key, _]) => key)
    }
    // Fallback: используем список всех стилей, исключая использованные
    return STYLE_VALUES.filter((s) => !usedStyles.includes(s))
  }

  const availableStylesList = getAvailableStylesList()
  const totalAvailable = availableStyles
    ? Object.values(availableStyles).filter((v) => v === 1).length
    : STYLE_COUNT - usedStyles.length

  const handleSubmit = (e) => {
    e.preventDefault()
    if (url.trim()) {
      onAnalyze(url.trim(), style, occasion.trim())
    }
  }

  const isValidUrl = (string) => {
    try {
      new URL(string)
      return true
    } catch (_) {
      return false
    }
  }

  const formatUrl = (url) => {
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      return `https://${url}`
    }
    return url
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <div className="card">
        <div className="text-center mb-8">
          <motion.div
            className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Search className="w-8 h-8 text-primary-600" />
          </motion.div>
          <h2 className="text-2xl font-display font-semibold text-gray-900 mb-2">
            Введите URL сайта для анализа
          </h2>
          <p className="text-gray-600">
            Укажите адрес веб-сайта, который хотите использовать
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
              URL сайта
            </label>
            <div className="relative">
              <input
                type="url"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                className={`input-field pr-10 ${urlLocked ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                required
                readOnly={urlLocked}
                title={urlLocked ? 'URL заблокирован. Обновите страницу для смены сайта.' : ''}
              />
              <ExternalLink className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
            {url && !isValidUrl(formatUrl(url)) && (
              <motion.p
                className="mt-2 text-sm text-red-600 flex items-center"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle className="w-4 h-4 mr-1" />
                Пожалуйста, введите корректный URL
              </motion.p>
            )}
          </div>

          <div>
            <label htmlFor="occasion" className="block text-sm font-medium text-gray-700 mb-2">
              Инфоповод / Причина публикации
            </label>
            <textarea
              id="occasion"
              value={occasion}
              onChange={(e) => setOccasion(e.target.value)}
              placeholder="Например: Грядущий Новый Год, День рождения компании, запуск новой акции..."
              className={`input-field resize-none ${occasionLocked ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              rows="3"
              readOnly={occasionLocked}
              title={occasionLocked ? 'Инфоповод заблокирован. Обновите страницу для изменения.' : ''}
            />
            <p className="mt-1 text-xs text-gray-500">
              Укажите повод или событие, для которого создаются публикации (необязательно)
            </p>
          </div>

          <div>
            <label htmlFor="style" className="block text-sm font-medium text-gray-700 mb-2">
              Публиковать в стиле: <span className="text-sm text-gray-500">({totalAvailable}/{STYLE_COUNT} доступно)</span>
            </label>
            <select
              id="style"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="input-field"
              disabled={availableStylesList.length === 0}
            >
              {availableStylesList.length === 0 ? (
                <option value="">Все стили использованы</option>
              ) : (
                STYLES.map(({ value, label }) => (
                  <option
                    key={value}
                    value={value}
                    disabled={!availableStylesList.includes(value)}
                  >
                    {usedStyles.includes(value) ? '✓ ' : ''}
                    {label}
                  </option>
                ))
              )}
            </select>
            {/* Сообщение "Все стили использованы" убрано - показывается модальное окно при попытке анализа */}
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

          {info && (
            <motion.div
              className="bg-blue-50 border border-blue-200 rounded-lg p-4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-blue-800">Информация</h3>
                  <p className="text-sm text-blue-700 mt-1">{info}</p>
                </div>
              </div>
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={!url.trim() || !isValidUrl(formatUrl(url))}
            className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            transition={{ duration: 0.2 }}
          >
            <span className="flex items-center justify-center">
              <Search className="w-5 h-5 mr-2" />
              Анализировать сайт
            </span>
          </motion.button>
        </form>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-4">💡 Как управлять генерацией:</h3>
          <div className="space-y-3 text-sm text-gray-600">
            <div className="flex items-start">
              <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                <span className="text-primary-600 font-semibold text-xs">1</span>
              </div>
              <p>Введите URL сайта, <strong className="text-primary-600">опционально укажите инфоповод</strong> (праздник, событие, акция) и выберите стиль публикации</p>
            </div>
            <div className="flex items-start">
              <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                <span className="text-primary-600 font-semibold text-xs">2</span>
              </div>
              <p>Получите 3 готовых поста объемом 400-800 символов каждый, адаптированных под указанный инфоповод</p>
            </div>
            <div className="flex items-start">
              <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                <span className="text-primary-600 font-semibold text-xs">3</span>
              </div>
              <p><strong className="text-primary-600">Быстрая смена стиля:</strong> Нажмите "Создать новые публикации" и выберите другой стиль — генерация займет всего ~10 секунд!</p>
            </div>
            <div className="flex items-start">
              <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                <span className="text-primary-600 font-semibold text-xs">💡</span>
              </div>
              <p className="text-primary-700 font-medium">Попробуйте разные стили для одного сайта и выберите лучший вариант!</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default SiteAnalyzer

