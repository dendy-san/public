import React, { useState, useEffect, useCallback } from 'react'
import { Users, Download, Search, AlertCircle, CheckCircle2, TrendingUp } from 'lucide-react'
import api, { downloadLeadsExport } from '../api.js'

// Превью перед выгрузкой: 4 поля по всем записям диапазона. Полный набор
// (14 полей) уходит в CSV — на экране лишние ПДн показывать незачем.
const COLUMNS = [
  { key: 'email', label: 'Email' },
  { key: 'status', label: 'Статус' },
  { key: 'created_at', label: 'Дата захвата' },
  { key: 'paid_at', label: 'Дата оплаты' },
]

const PAGE_SIZE = 50

const STATUS_LABELS = {
  all: 'Все',
  new: 'Новые',
  paid: 'Оплаченные',
  expired: 'Истёкшие',
}

const fmtDateTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Сегодня в формате YYYY-MM-DD — дефолт правой границы диапазона.
const todayISO = () => new Date().toISOString().slice(0, 10)

// Дата на N дней назад — дефолт левой границы, чтобы таблица не открывалась пустой.
const daysAgoISO = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function LeadsPanel() {
  const [leads, setLeads] = useState([])
  const [total, setTotal] = useState(0)
  const [funnel, setFunnel] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [status, setStatus] = useState('all')
  const [dateFrom, setDateFrom] = useState(daysAgoISO(30))
  const [dateTo, setDateTo] = useState(todayISO())
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  const buildQuery = useCallback(() => {
    const p = new URLSearchParams()
    if (status && status !== 'all') p.set('status', status)
    if (dateFrom) p.set('date_from', dateFrom)
    if (dateTo) p.set('date_to', dateTo)
    if (search.trim()) p.set('search', search.trim())
    return p
  }, [status, dateFrom, dateTo, search])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const p = buildQuery()
      p.set('limit', PAGE_SIZE)
      p.set('offset', page * PAGE_SIZE)
      const response = await api.get(`/leads?${p.toString()}`)
      setLeads(response.data.leads || [])
      setTotal(response.data.total || 0)
      setFunnel(response.data.funnel || null)
    } catch (err) {
      console.error('Ошибка загрузки лидов:', err)
      setError(err.response?.data?.detail || 'Не удалось загрузить лиды')
    } finally {
      setLoading(false)
    }
  }, [buildQuery, page])

  useEffect(() => {
    load()
  }, [load])

  // Смена фильтра возвращает на первую страницу, иначе можно остаться
  // на offset, за пределами новой (меньшей) выборки, и увидеть пустоту.
  const applyFilter = (setter) => (value) => {
    setter(value)
    setPage(0)
  }

  const [exporting, setExporting] = useState(false)

  const exportCsv = async () => {
    // Экспорт использует тот же фильтр, что и таблица: превью и файл
    // должны совпадать по составу записей.
    //
    // Переходом по ссылке здесь не обойтись: вместе с навигацией браузер не
    // передаёт заголовок Authorization, и backend ответил бы 401 вместо файла.
    setExporting(true)
    setError('')
    try {
      await downloadLeadsExport(buildQuery().toString())
    } catch (err) {
      console.error('Ошибка выгрузки CSV:', err)
      setError('Не удалось выгрузить CSV')
    } finally {
      setExporting(false)
    }
  }

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-6">
      {/* Воронка: ради этих цифр таблица и заведена */}
      {funnel && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-indigo-600" />
            Воронка
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'Всего лидов', value: funnel.total },
              { label: 'Новые', value: funnel.new },
              { label: 'Оплачено', value: funnel.paid },
              { label: 'Истекло', value: funnel.expired },
              { label: 'Выручка, ₽', value: funnel.revenue },
              { label: 'Конверсия', value: `${funnel.conversion_pct}%` },
            ].map((item) => (
              <div key={item.label} className="text-center p-3 bg-indigo-50 rounded-lg">
                <div className="text-2xl font-bold text-indigo-700">{item.value}</div>
                <div className="text-xs text-gray-600 mt-1">{item.label}</div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-4">
            Согласий с обеими отметками: {funnel.consented} из {funnel.total}.
            Конверсия считается по всем лидам, включая неоплаченные.
          </p>
        </div>
      )}

      {/* Фильтры */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-600" />
            Лиды
          </h2>
          <button
            onClick={exportCsv}
            disabled={loading || total === 0 || exporting}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            Экспорт CSV ({total})
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Статус</label>
            <select
              value={status}
              onChange={(e) => applyFilter(setStatus)(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Дата с</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => applyFilter(setDateFrom)(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Дата по</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => applyFilter(setDateTo)(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Поиск по email</label>
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => applyFilter(setSearch)(e.target.value)}
                placeholder="part@domain"
                className="w-full px-3 py-2 pr-9 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Превью: 4 поля по всем записям диапазона */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left">
                {COLUMNS.map((c) => (
                  <th key={c.key} className="py-2 px-3 font-medium text-gray-600">{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="py-8 text-center text-gray-500">
                    {loading ? 'Загрузка…' : 'Нет записей в выбранном диапазоне'}
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.email} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3 font-mono text-gray-800">{lead.email}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        lead.status === 'paid'
                          ? 'bg-green-100 text-green-700'
                          : lead.status === 'expired'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {STATUS_LABELS[lead.status] || lead.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-gray-600">{fmtDateTime(lead.created_at)}</td>
                    <td className="py-2 px-3 text-gray-600">{fmtDateTime(lead.paid_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Пагинация */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
            <span>
              Показано {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} из {total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0 || loading}
                className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Назад
              </button>
              <span className="px-3 py-1">{page + 1} / {pages}</span>
              <button
                onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                disabled={page + 1 >= pages || loading}
                className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Вперёд
              </button>
            </div>
          </div>
        )}

        {!loading && leads.length > 0 && (
          <p className="text-xs text-gray-500 mt-3 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            В CSV уйдут все {total} записей диапазона и 14 полей, включая согласия, IP и срок удаления.
          </p>
        )}
      </div>
    </div>
  )
}

export default LeadsPanel
