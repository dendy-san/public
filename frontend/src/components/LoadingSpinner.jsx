import React from 'react'
import { motion } from 'framer-motion'
import { Loader2, Globe } from 'lucide-react'

const LoadingSpinner = () => {
  return (
    <div className="text-center">
      <motion.div
        className="relative"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Outer rotating ring */}
        <motion.div
          className="w-20 h-20 border-4 border-primary-200 border-t-primary-600 rounded-full mx-auto mb-6"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
        
        {/* Inner icon */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{ rotate: -360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <Globe className="w-8 h-8 text-primary-600" />
        </motion.div>
      </motion.div>

      <motion.h3
        className="text-xl font-display font-semibold text-gray-900 mb-2"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        Анализируем сайт...
      </motion.h3>
      
      <motion.p
        className="text-gray-600 max-w-md mx-auto"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        Это может занять несколько минут. Мы изучаем содержимое сайта и формируем посты.
      </motion.p>

      {/* Animated dots */}
      <motion.div
        className="flex justify-center space-x-1 mt-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
      >
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 bg-primary-500 rounded-full"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: i * 0.2,
            }}
          />
        ))}
      </motion.div>
    </div>
  )
}

export default LoadingSpinner









