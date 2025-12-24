import React from 'react'
import { motion } from 'framer-motion'

const AnalysisCard = ({ title, icon, content, delay = 0 }) => {
  return (
    <motion.div
      className="card group hover:shadow-2xl transition-all duration-300"
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ 
        duration: 0.6, 
        delay: delay,
        ease: "easeOut"
      }}
      whileHover={{ 
        y: -5,
        transition: { duration: 0.2 }
      }}
    >
      <motion.div
        className="flex items-center space-x-3 mb-4"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: delay + 0.2 }}
      >
        <motion.div
          className="p-2 bg-primary-100 rounded-lg text-primary-600 group-hover:bg-primary-200 transition-colors duration-200"
          whileHover={{ scale: 1.1, rotate: 5 }}
          transition={{ duration: 0.2 }}
        >
          {icon}
        </motion.div>
        <h3 className="text-xl font-display font-semibold text-gray-900 group-hover:text-primary-700 transition-colors duration-200">
          {title}
        </h3>
      </motion.div>
      
      <motion.div
        className="text-gray-700"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: delay + 0.3 }}
      >
        {content}
      </motion.div>
    </motion.div>
  )
}

export default AnalysisCard









