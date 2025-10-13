import React from 'react';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Star, 
  TrendingUp, 
  Users, 
  FileText, 
  MessageSquare,
  Award,
  Target,
  Lightbulb,
  Shield
} from 'lucide-react';
import { 
  parseLLMResponse, 
  extractThought, 
  getScoreColor, 
  getDecisionColor, 
  formatScore, 
  getScorePercentage 
} from '../utils/responseParser';

const ResultsDisplay = ({ response }) => {
  const parsedData = parseLLMResponse(response);
  const thought = extractThought(response);

  if (!parsedData) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2" />
          <p className="text-yellow-800">Не удалось распарсить результаты. Показываем сырой ответ.</p>
        </div>
        <div className="mt-4 bg-gray-900 text-green-400 rounded-lg p-4 max-h-96 overflow-y-auto">
          <pre className="whitespace-pre-wrap text-sm">{response}</pre>
        </div>
      </div>
    );
  }

  const {
    Summary,
    Strengths = [],
    Weaknesses = [],
    Relevance,
    Literature_and_Originality,
    Practical_Significance,
    Author_Contribution,
    Presentation_and_QA,
    PresentationNotes = [],
    Soundness,
    Questions = [],
    Limitations = [],
    Ethical_Concerns,
    Overall,
    Confidence,
    Decision
  } = parsedData;

  // Убеждаемся, что все поля являются массивами
  const safeStrengths = Array.isArray(Strengths) ? Strengths : [];
  const safeWeaknesses = Array.isArray(Weaknesses) ? Weaknesses : [];
  const safePresentationNotes = Array.isArray(PresentationNotes) ? PresentationNotes : [];
  const safeQuestions = Array.isArray(Questions) ? Questions : [];
  const safeLimitations = Array.isArray(Limitations) ? Limitations : [];

  const metrics = [
    { label: 'Релевантность', value: Relevance, icon: Target },
    { label: 'Литература и оригинальность', value: Literature_and_Originality, icon: FileText },
    { label: 'Практическая значимость', value: Practical_Significance, icon: TrendingUp },
    { label: 'Вклад автора', value: Author_Contribution, icon: Users },
    { label: 'Презентация и Q&A', value: Presentation_and_QA, icon: MessageSquare },
    { label: 'Обоснованность', value: Soundness, icon: Shield }
  ];

  return (
    <div className="space-y-6">
      {/* Заголовок с общим решением */}
      <div className="result-section">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-2xl font-bold text-gray-900">Результаты оценки</h3>
          <div className={`px-4 py-2 rounded-full text-sm font-medium ${getDecisionColor(Decision)}`}>
            {Decision || 'Не определено'}
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{formatScore(Overall)}</div>
            <div className="text-sm text-gray-600">Общая оценка</div>
            <div className="progress-bar mt-2">
              <div 
                className={`progress-fill ${getScoreColor(Overall).split(' ')[0].replace('text-', 'bg-')}`}
                style={{ width: `${getScorePercentage(Overall)}%` }}
              ></div>
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{formatScore(Confidence)}</div>
            <div className="text-sm text-gray-600">Уверенность</div>
            <div className="progress-bar mt-2">
              <div 
                className={`progress-fill ${getScoreColor(Confidence).split(' ')[0].replace('text-', 'bg-')}`}
                style={{ width: `${getScorePercentage(Confidence)}%` }}
              ></div>
            </div>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center">
              {Ethical_Concerns === true ? (
                <XCircle className="w-8 h-8 text-red-500" />
              ) : (
                <CheckCircle className="w-8 h-8 text-green-500" />
              )}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              {Ethical_Concerns === true ? 'Этические проблемы' : 'Этически корректно'}
            </div>
          </div>
        </div>
      </div>

      {/* Краткое резюме */}
      {Summary && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <FileText className="w-5 h-5 mr-2" />
            Краткое резюме
          </h4>
          <p className="text-gray-700 leading-relaxed">{Summary}</p>
        </div>
      )}

      {/* Метрики оценки */}
      <div className="result-section">
        <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Award className="w-5 h-5 mr-2" />
          Детальная оценка
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {metrics.map((metric, index) => {
            const Icon = metric.icon;
            return (
              <div key={index} className="metric-card">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <Icon className="w-4 h-4 text-gray-600 mr-2" />
                    <span className="text-sm font-medium text-gray-700">{metric.label}</span>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(metric.value)}`}>
                    {formatScore(metric.value)}
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className={`progress-fill ${getScoreColor(metric.value).split(' ')[0].replace('text-', 'bg-')}`}
                    style={{ width: `${getScorePercentage(metric.value)}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Сильные стороны */}
      {safeStrengths.length > 0 && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
            Сильные стороны
          </h4>
          <ul className="space-y-2">
            {safeStrengths.map((strength, index) => (
              <li key={index} className="strength-item">
                <Star className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{strength}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Слабые стороны */}
      {safeWeaknesses.length > 0 && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <XCircle className="w-5 h-5 mr-2 text-red-600" />
            Области для улучшения
          </h4>
          <ul className="space-y-2">
            {safeWeaknesses.map((weakness, index) => (
              <li key={index} className="weakness-item">
                <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{weakness}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Замечания по презентации */}
      {safePresentationNotes.length > 0 && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <MessageSquare className="w-5 h-5 mr-2 text-blue-600" />
            Замечания по презентации
          </h4>
          <ul className="space-y-2">
            {safePresentationNotes.map((note, index) => (
              <li key={index} className="flex items-start">
                <Lightbulb className="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Вопросы */}
      {safeQuestions.length > 0 && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <MessageSquare className="w-5 h-5 mr-2 text-purple-600" />
            Вопросы для обсуждения
          </h4>
          <ul className="space-y-2">
            {safeQuestions.map((question, index) => (
              <li key={index} className="question-item">
                <span className="icon-badge bg-purple-100 text-purple-600">
                  {index + 1}
                </span>
                <span className="text-gray-700">{question}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ограничения */}
      {safeLimitations.length > 0 && (
        <div className="result-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2 text-orange-600" />
            Ограничения
          </h4>
          <ul className="space-y-2">
            {safeLimitations.map((limitation, index) => (
              <li key={index} className="limitation-item">
                <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{limitation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Мысли эксперта */}
      {thought && (
        <div className="thought-section">
          <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <Lightbulb className="w-5 h-5 mr-2 text-blue-600" />
            Мысли эксперта
          </h4>
          <p className="text-gray-700 leading-relaxed italic">{thought}</p>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;
