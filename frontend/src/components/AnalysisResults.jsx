import React from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, CheckCircle2, Globe, Users, Star, Phone, MapPin, Download, Calendar } from 'lucide-react'
import AnalysisCard from './AnalysisCard'
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } from 'docx'
import { saveAs } from 'file-saver'

const AnalysisResults = ({ data, onReset }) => {
  const { final: finalAnalysis, url, style, occasion } = data

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 }
    }
  }

  const renderValue = (value, key) => {
    if (typeof value === 'string') {
      return <p className="text-gray-700 whitespace-pre-wrap">{value}</p>
    }
    
    if (Array.isArray(value)) {
      // Специальное отображение для постов соцсети
      if (key === 'posts') {
        return (
          <div className="space-y-4">
            {value.map((item, index) => (
              <motion.div
                key={index}
                className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-primary-600">
                    Пост #{index + 1}
                  </span>
                  <span className="text-xs text-gray-500">
                    {item.length} символов
                  </span>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{item}</p>
              </motion.div>
            ))}
          </div>
        )
      }
      
      return (
        <ul className="space-y-2">
          {value.map((item, index) => (
            <motion.li
              key={index}
              className="flex items-start"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <CheckCircle2 className="w-4 h-4 text-green-500 mt-1 mr-2 flex-shrink-0" />
              <span className="text-gray-700">{item}</span>
            </motion.li>
          ))}
        </ul>
      )
    }
    
    if (typeof value === 'object' && value !== null) {
      return (
        <div className="space-y-3">
          {Object.entries(value).map(([subKey, subValue]) => (
            <div key={subKey} className="border-l-2 border-primary-200 pl-4">
              <h4 className="font-medium text-gray-900 capitalize mb-1">
                {subKey.replace(/_/g, ' ')}
              </h4>
              <div className="text-gray-700">
                {renderValue(subValue, subKey)}
              </div>
            </div>
          ))}
        </div>
      )
    }
    
    return <p className="text-gray-700">{String(value)}</p>
  }

  const getIconForKey = (key) => {
    const keyLower = key.toLowerCase()
    if (keyLower.includes('контакт') || keyLower.includes('телефон')) return <Phone className="w-5 h-5" />
    if (keyLower.includes('адрес') || keyLower.includes('координат')) return <MapPin className="w-5 h-5" />
    if (keyLower.includes('услуг') || keyLower.includes('развлечен')) return <Star className="w-5 h-5" />
    if (keyLower.includes('номер')) return <Users className="w-5 h-5" />
    return <Globe className="w-5 h-5" />
  }

  const getTitleForKey = (key) => {
    const titles = {
      'posts': style ? `Публикации для соцсетей в ${style} стиле` : 'Публикации для соцсетей',
      'название': 'Название',
      'описание': 'Описание',
      'причины_выбрать': 'Причины выбрать',
      'услуги': 'Услуги',
      'номера': 'Номера',
      'питание': 'Питание',
      'развлечения': 'Развлечения',
      'контакты': 'Контактная информация'
    }
    return titles[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const handleDownloadReport = async () => {
    // Получаем посты из финального анализа
    const posts = finalAnalysis.posts || []
    
    // Создаём параграфы для документа
    const docParagraphs = [
      // Заголовок
      new Paragraph({
        text: 'ОТЧЁТ ПО ГЕНЕРАЦИИ ПУБЛИКАЦИЙ',
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 }
      }),

      // Информация о сайте
      new Paragraph({
        children: [
          new TextRun({
            text: 'Сайт: ',
            bold: true
          }),
          new TextRun(url)
        ],
        spacing: { after: 200 }
      }),

      // Инфоповод (если есть)
      ...(occasion && occasion.trim() ? [
        new Paragraph({
          children: [
            new TextRun({
              text: 'Инфоповод: ',
              bold: true
            }),
            new TextRun(occasion)
          ],
          spacing: { after: 200 }
        })
      ] : []),

      // Стиль
      new Paragraph({
        children: [
          new TextRun({
            text: 'Публикации в стиле: ',
            bold: true
          }),
          new TextRun(style)
        ],
        spacing: { after: 200 }
      }),

      // Дата создания
      new Paragraph({
        children: [
          new TextRun({
            text: 'Дата создания: ',
            bold: true
          }),
          new TextRun(new Date().toLocaleString('ru-RU'))
        ],
        spacing: { after: 400 }
      }),

      // Разделитель
      new Paragraph({
        text: '',
        border: {
          bottom: {
            color: '000000',
            space: 1,
            style: BorderStyle.SINGLE,
            size: 6
          }
        },
        spacing: { after: 400 }
      }),

      // Заголовок секции постов
      new Paragraph({
        text: 'ПУБЛИКАЦИИ ДЛЯ СОЦСЕТЕЙ',
        heading: HeadingLevel.HEADING_1,
        spacing: { after: 300 }
      })
    ]

    // Добавляем каждый пост
    posts.forEach((post, index) => {
      const charCount = post.length
      
      docParagraphs.push(
        // Номер поста и количество символов
        new Paragraph({
          children: [
            new TextRun({
              text: `Пост ${index + 1}`,
              bold: true,
              size: 28
            }),
            new TextRun({
              text: ` (${charCount} символов)`,
              italics: true,
              size: 24,
              color: '666666'
            })
          ],
          spacing: { before: 300, after: 200 }
        }),
        
        // Текст поста
        new Paragraph({
          text: post,
          spacing: { after: 400 },
          alignment: AlignmentType.JUSTIFIED
        })
      )
    })

    // Футер
    docParagraphs.push(
      new Paragraph({
        text: '',
        border: {
          top: {
            color: '000000',
            space: 1,
            style: BorderStyle.SINGLE,
            size: 6
          }
        },
        spacing: { before: 400, after: 200 }
      }),
      new Paragraph({
        text: 'Создано генератором публикаций',
        alignment: AlignmentType.CENTER,
        italics: true,
        spacing: { after: 200 }
      })
    )

    // Создаём документ
    const doc = new Document({
      sections: [{
        properties: {},
        children: docParagraphs
      }]
    })

    // Генерируем и сохраняем файл
    try {
      const blob = await Packer.toBlob(doc)
      const fileName = `публикации_${url.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.docx`
      saveAs(blob, fileName)
    } catch (error) {
      console.error('Ошибка при создании документа:', error)
      alert('Не удалось создать документ. Попробуйте ещё раз.')
    }
  }

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center">
        <div className="flex items-center justify-between mb-6">
          <motion.button
            onClick={onReset}
            className="btn-secondary flex items-center"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Создать новые публикации
          </motion.button>
          <div className="flex-1"></div>
        </div>
        
        <div className="card max-w-2xl mx-auto">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <CheckCircle2 className="w-8 h-8 text-green-500" />
            <h2 className="text-2xl font-display font-bold text-gray-900">
              Публикации готовы
            </h2>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-center space-x-2 text-gray-600">
              <Globe className="w-4 h-4" />
              <span className="font-medium">{url}</span>
            </div>
            {occasion && occasion.trim() && (
              <div className="flex items-center justify-center space-x-2 text-primary-600">
                <Calendar className="w-4 h-4" />
                <span className="font-medium">Инфоповод: {occasion}</span>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Analysis Cards */}
      <motion.div
        variants={containerVariants}
        className="grid gap-6"
      >
        {Object.entries(finalAnalysis).map(([key, value], index) => (
          <motion.div
            key={key}
            variants={itemVariants}
            className="w-full"
          >
            <AnalysisCard
              title={getTitleForKey(key)}
              icon={getIconForKey(key)}
              content={renderValue(value, key)}
              delay={index * 0.1}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Download Report Button */}
      <motion.div
        variants={itemVariants}
        className="flex justify-center pt-4"
      >
        <motion.button
          onClick={handleDownloadReport}
          className="btn-primary flex items-center space-x-2 px-8 py-3 text-lg"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Download className="w-5 h-5" />
          <span>Сохранить отчёт</span>
        </motion.button>
      </motion.div>
    </motion.div>
  )
}

export default AnalysisResults

