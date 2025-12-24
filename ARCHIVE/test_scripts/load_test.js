import http from 'k6/http';
import { check, sleep } from 'k6';

// Конфигурация теста
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Разогрев: 10 пользователей за 30 сек
    { duration: '60s', target: 25 },  // Рост: 25 пользователей за 60 сек
    { duration: '120s', target: 50 }, // Целевая нагрузка: 50 пользователей за 2 мин
    { duration: '60s', target: 25 },  // Снижение: 25 пользователей за 60 сек
    { duration: '30s', target: 0 },   // Завершение: 0 пользователей за 30 сек
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% запросов должны быть быстрее 2 сек
    http_req_failed: ['rate<0.01'],    // Менее 1% ошибок
    http_reqs: ['rate>10'],            // Минимум 10 RPS
  },
};

const BASE_URL = 'http://localhost:8000';

// Тестовые данные
const testUrls = [
  'https://example.com',
  'https://httpbin.org/html',
  'https://jsonplaceholder.typicode.com',
];

const testStyles = [
  'убедительно-позитивном',
  'информационном',
  'разговорном',
  'продающем'
];

export default function() {
  // Тест 1: Лёгкие эндпоинты (chat)
  const chatPayload = {
    prompt: `Привет! Расскажи кратко о ${testUrls[Math.floor(Math.random() * testUrls.length)]}`,
    temperature: 0.7,
    max_tokens: 100
  };

  let response = http.post(`${BASE_URL}/llm/chat`, JSON.stringify(chatPayload), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(response, {
    'chat status is 200': (r) => r.status === 200,
    'chat response time < 2s': (r) => r.timings.duration < 2000,
    'chat has text': (r) => r.json('text') && r.json('text').length > 0,
  });

  sleep(1);

  // Тест 2: JSON эндпоинт
  const jsonPayload = {
    system_prompt: 'Отвечай в формате JSON с полями title (строка) и description (строка)',
    user_prompt: `Опиши сайт ${testUrls[Math.floor(Math.random() * testUrls.length)]}`,
    temperature: 0.3
  };

  response = http.post(`${BASE_URL}/llm/chat-json`, JSON.stringify(jsonPayload), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(response, {
    'chat-json status is 200': (r) => r.status === 200,
    'chat-json response time < 3s': (r) => r.timings.duration < 3000,
    'chat-json has title': (r) => r.json('title') && r.json('title').length > 0,
  });

  sleep(2);

  // Тест 3: Анализ сайта (только отправка задачи, не ждём результата)
  const analyzePayload = {
    url: testUrls[Math.floor(Math.random() * testUrls.length)],
    style: testStyles[Math.floor(Math.random() * testStyles.length)],
    occasion: Math.random() > 0.5 ? 'Новогодние праздники' : ''
  };

  response = http.post(`${BASE_URL}/llm/analyze-site`, JSON.stringify(analyzePayload), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(response, {
    'analyze-site status is 200': (r) => r.status === 200,
    'analyze-site response time < 1s': (r) => r.timings.duration < 1000,
    'analyze-site returns task_id': (r) => r.json('task_id') && r.json('task_id').length > 0,
    'analyze-site status is submitted': (r) => r.json('status') === 'submitted',
  });

  // Если получили task_id, проверим статус (с небольшой задержкой)
  if (response.json('task_id')) {
    sleep(1);
    
    const taskId = response.json('task_id');
    const statusResponse = http.get(`${BASE_URL}/llm/task-status/${taskId}`);
    
    check(statusResponse, {
      'task-status status is 200': (r) => r.status === 200,
      'task-status has status field': (r) => r.json('status') !== undefined,
    });
  }

  sleep(Math.random() * 2); // Случайная пауза 0-2 сек
}

// Функция для проверки health endpoint
export function setup() {
  const response = http.get(`${BASE_URL}/health`);
  if (response.status !== 200) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  console.log('Health check passed, starting load test...');
}







