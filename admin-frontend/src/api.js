import axios from 'axios'

/**
 * Единая точка доступа к админ-API.
 *
 * Все запросы идут с заголовком Authorization: Bearer <токен>, который
 * backend требует для всего блока /admin (см. app/services/admin_auth.py):
 * там персональные данные клиентов и реквизиты платежей.
 *
 * Токен хранится в sessionStorage, а не в localStorage: доступ к ПДн не
 * должен переживать закрытие вкладки, иначе админку можно открыть с чужого
 * разблокированного компьютера.
 */

const TOKEN_KEY = 'admin_token'

// В dev — vite proxy (vite.config.js). VITE_API_URL переопределяет на другой
// домен; по умолчанию относительный путь, и nginx контейнера проксирует сам.
export const API_URL = `${import.meta.env.VITE_API_URL ?? ''}/admin`

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

const api = axios.create({ baseURL: API_URL })

// Заголовок подставляется на каждый запрос, а не один раз при создании
// инстанса: токен может появиться (вход) или измениться уже после импорта.
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401/503 означают, что токен неверен или не настроен: возвращаем на экран
// входа, чтобы панели не показывали пустые таблицы с непонятной ошибкой.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 503) {
      clearToken()
      window.dispatchEvent(new Event('admin-unauthorized'))
    }
    return Promise.reject(error)
  }
)

/**
 * Выгрузка CSV. Обычная ссылка (window.location.href) здесь не годится:
 * вместе с переходом браузер не передаёт заголовок Authorization, и backend
 * ответит 401 вместо файла.
 */
export async function downloadLeadsExport(query) {
  const response = await api.get(`/leads/export?${query}`, {
    responseType: 'blob',
  })

  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url

  // Имя файла берём из Content-Disposition, чтобы дата в нём ставилась на
  // сервере; если заголовка нет — генерируем локально.
  const disposition = response.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^";]+)"?/)
  link.download = match ? match[1] : `leads-${new Date().toISOString().slice(0, 10)}.csv`

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export default api
