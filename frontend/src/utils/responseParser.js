/**
 * Парсит ответ от LLM и извлекает JSON данные
 * @param {string} response - Полный ответ от LLM
 * @returns {Object} - Объект с parsed данными или null если парсинг не удался
 */
export const parseLLMResponse = (response) => {
  try {
    // Ищем JSON блок в ответе
    const jsonMatch = response.match(/<JSON>(.*?)<\/JSON>/s);
    
    if (jsonMatch) {
      const jsonString = jsonMatch[1].trim();
      const parsed = JSON.parse(jsonString);
      return ensureArrayFields(parsed);
    }
    
    // Если нет тегов JSON, ищем просто JSON объект
    const jsonStart = response.indexOf('{');
    const jsonEnd = response.lastIndexOf('}');
    
    if (jsonStart !== -1 && jsonEnd !== -1 && jsonEnd > jsonStart) {
      const jsonString = response.substring(jsonStart, jsonEnd + 1);
      const parsed = JSON.parse(jsonString);
      return ensureArrayFields(parsed);
    }
    
    return null;
  } catch (error) {
    console.error('Error parsing LLM response:', error);
    return null;
  }
};

// Функция для обеспечения того, что все поля-массивы действительно являются массивами
const ensureArrayFields = (data) => {
  if (!data || typeof data !== 'object') return data;
  
  const arrayFields = ['Strengths', 'Weaknesses', 'PresentationNotes', 'Questions', 'Limitations'];
  
  arrayFields.forEach(field => {
    if (data[field] && !Array.isArray(data[field])) {
      // Если поле существует, но не является массивом, преобразуем его
      if (typeof data[field] === 'string') {
        data[field] = [data[field]];
      } else {
        data[field] = [];
      }
    } else if (!data[field]) {
      data[field] = [];
    }
  });
  
  return data;
};

/**
 * Извлекает THOUGHT блок из ответа
 * @param {string} response - Полный ответ от LLM
 * @returns {string} - Текст из THOUGHT блока или пустая строка
 */
export const extractThought = (response) => {
  try {
    const thoughtMatch = response.match(/<THOUGHT>(.*?)<\/THOUGHT>/s);
    return thoughtMatch ? thoughtMatch[1].trim() : '';
  } catch (error) {
    console.error('Error extracting thought:', error);
    return '';
  }
};

/**
 * Получает цвет для оценки
 * @param {number} score - Оценка от 1 до 10
 * @returns {string} - CSS класс для цвета
 */
export const getScoreColor = (score) => {
  if (typeof score !== 'number' || isNaN(score)) {
    return 'text-gray-600 bg-gray-100';
  }
  
  if (score >= 8) return 'text-green-600 bg-green-100';
  if (score >= 6) return 'text-yellow-600 bg-yellow-100';
  if (score >= 4) return 'text-orange-600 bg-orange-100';
  return 'text-red-600 bg-red-100';
};

/**
 * Получает цвет для решения
 * @param {string} decision - Решение (Accept, Reject, etc.)
 * @returns {string} - CSS класс для цвета
 */
export const getDecisionColor = (decision) => {
  if (!decision || typeof decision !== 'string') {
    return 'text-gray-600 bg-gray-100';
  }
  
  const decisionLower = decision.toLowerCase();
  if (decisionLower.includes('accept')) return 'text-green-600 bg-green-100';
  if (decisionLower.includes('reject')) return 'text-red-600 bg-red-100';
  return 'text-gray-600 bg-gray-100';
};

/**
 * Форматирует оценку для отображения
 * @param {number} score - Оценка
 * @returns {string} - Форматированная оценка
 */
export const formatScore = (score) => {
  if (typeof score !== 'number') return 'N/A';
  return `${score}/10`;
};

/**
 * Получает процентное значение для прогресс-бара
 * @param {number} score - Оценка от 1 до 10
 * @returns {number} - Процент от 0 до 100
 */
export const getScorePercentage = (score) => {
  if (typeof score !== 'number' || isNaN(score)) return 0;
  return Math.max(0, Math.min(100, (score / 10) * 100));
};
