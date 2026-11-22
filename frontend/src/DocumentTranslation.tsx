import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';

type Language = 'en' | 'ar';
type View = 'original' | 'translation' | 'parallel';
type Target = Language | 'auto';
type Result = {
  source_language: Language;
  target_language: Language;
  mixed: boolean;
  clauses: {id: string; page: number; text: string; translation: string}[];
};
export type TranslationCache = Partial<Record<Target, Result>>;

const copy = {
  en: {
    views: 'Document view', original: 'Original', translation: 'Translation', parallel: 'Side-by-side',
    target: 'Translate to', auto: 'Opposite of detected language', en: 'English', ar: 'Arabic',
    start: 'Translate with Ollama', working: 'Translating locally. Longer documents may take a few minutes.',
    retry: 'Retry translation', page: 'Page', clause: 'Clause', source: 'Detected source',
    mixed: 'Mixed English and Arabic',
    notice: 'AI-generated on this device for information only. This is not a certified translation. Check the original before relying on it.',
    unverified: 'The translation could not be checked against the original. Retry, or open Original to review the source.',
    unavailable: 'The local Ollama model is unavailable. Start Ollama with qwen3:4b and retry.',
    timeout: 'The local model timed out. Retry translation.',
    same: 'This document already uses that language. Choose a different target.',
    invalid: 'This PDF could not be translated. Make sure it has selectable text and can be opened.',
  },
  ar: {
    views: 'عرض المستند', original: 'الأصل', translation: 'الترجمة', parallel: 'عرض متوازٍ',
    target: 'الترجمة إلى', auto: 'اللغة الأخرى تلقائيًا', en: 'الإنجليزية', ar: 'العربية',
    start: 'ترجمة عبر Ollama', working: 'تجري الترجمة محليًا. قد تستغرق المستندات الطويلة بضع دقائق.',
    retry: 'إعادة محاولة الترجمة', page: 'الصفحة', clause: 'البند', source: 'لغة المستند المحددة',
    mixed: 'العربية والإنجليزية',
    notice: 'ترجمة آلية محلية لأغراض معلوماتية، وهي غير معتمدة. راجع النص الأصلي قبل الاعتماد عليها.',
    unverified: 'تعذر التحقق من مطابقة الترجمة للأصل. أعد المحاولة أو افتح النص الأصلي للمراجعة.',
    unavailable: 'نموذج Ollama المحلي غير متاح. شغّل Ollama مع qwen3:4b ثم أعد المحاولة.',
    timeout: 'انتهت مهلة استجابة النموذج المحلي. أعد محاولة الترجمة.',
    same: 'المستند مكتوب بهذه اللغة بالفعل. اختر لغة أخرى للترجمة.',
    invalid: 'تعذرت ترجمة هذا الملف. تأكد من إمكانية فتحه وتحديد النص داخله.',
  },
};
const errors = {
  translation_unverified: 'unverified',
  translation_unavailable: 'unavailable',
  translation_timeout: 'timeout',
  translation_same_language: 'same',
} as const;
type ErrorKey = typeof errors[keyof typeof errors] | 'invalid';

type Props = {
  api: string;
  lang: Language;
  file: File | null;
  sampleId: string;
  findingId?: string;
  findingClauses?: string[];
  cache: TranslationCache;
  setCache: (update: (previous: TranslationCache) => TranslationCache) => void;
  original: ReactNode;
};

export default function DocumentTranslation({
  api, lang, file, sampleId, findingId, findingClauses, cache, setCache, original,
}: Props) {
  const t = copy[lang];
  const [view, setView] = useState<View>('original');
  const [target, setTarget] = useState<Target>('auto');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [selected, setSelected] = useState<string>();
  const request = useRef<AbortController | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const result = cache[target];
  const linkedClause = findingClauses?.[0];

  useLayoutEffect(() => () => request.current?.abort(), []);
  useEffect(() => setSelected(linkedClause), [findingId, linkedClause]);
  useEffect(() => {
    if (view === 'original' || !selected || !result) return;
    const container = list.current;
    const row = container?.querySelector<HTMLElement>(`[data-clause="${CSS.escape(selected)}"]`);
    if (container && row) container.scrollTop = row.offsetTop;
  }, [findingId, result, selected, view]);

  async function translate() {
    if (result || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(null);
    const query = new URLSearchParams({target});
    let form: FormData | undefined;
    if (file) {
      form = new FormData();
      form.append('file', file);
    } else {
      query.set('lang', lang);
      query.set('sample_id', sampleId);
    }
    try {
      const response = await fetch(`${api}/api/translate-${file ? 'file' : 'sample'}?${query}`, {
        method: 'POST', body: form, signal: controller.signal,
      });
      const data = await response.json();
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setError(errors[data.detail as keyof typeof errors] || 'invalid');
        return;
      }
      const result: Result = data;
      setCache(previous => ({
        ...previous,
        [target]: result,
        [result.target_language]: result,
        ...(result.source_language !== result.target_language && {auto: result}),
      }));
    } catch {
      if (!controller.signal.aborted) setError('unavailable');
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <>
    <div className="document-modes" role="group" aria-label={t.views}>
      {(['original', 'translation', 'parallel'] as const).map(mode =>
        <button key={mode} type="button" aria-pressed={view === mode} onClick={() => setView(mode)}>
          {t[mode]}
        </button>)}
    </div>
    <div className="document-original" hidden={view !== 'original'}>{original}</div>
    {view !== 'original' && <div className="translation-workspace" aria-busy={busy}>
      <p className="translation-note">{t.notice}</p>
      <div className="translation-controls">
        <label>{t.target}
          <select value={target} disabled={busy} onChange={event => {
            setTarget(event.target.value as Target);
            setError(null);
          }}>
            <option value="auto">{t.auto}</option>
            <option value="ar">{t.ar}</option>
            <option value="en">{t.en}</option>
          </select>
        </label>
        {!result && <button className="outline" type="button" disabled={busy} onClick={translate}>
          {error ? t.retry : t.start}
        </button>}
      </div>
      {busy && <p role="status">{t.working}</p>}
      {error && <p className="translation-error" role="alert">{t[error]}</p>}
      {result && <>
        <p className="translation-note">{t.source} · {result.mixed ? t.mixed : t[result.source_language]}</p>
        <div className="translation-clauses" ref={list}>
          {result.clauses.map(clause => {
            const active = clause.id === selected;
            return <article key={clause.id} data-clause={clause.id}
              className={active || findingClauses?.includes(clause.id) ? 'translation-linked' : undefined}>
              <button className="translation-clause-label" type="button" aria-pressed={active}
                onClick={() => setSelected(active ? undefined : clause.id)}>
                {t.clause} <bdi>{clause.id}</bdi> · {t.page} {clause.page}
              </button>
              <div className={view === 'parallel' ? 'translation-pair' : undefined}>
                {(view === 'parallel' || active) && <div className="translated-source">
                  <h3>{t.original}</h3><p dir="auto">{clause.text}</p>
                </div>}
                <div className="translated-text">
                  {view === 'parallel' && <h3>{t.translation}</h3>}
                  <p lang={result.target_language} dir={result.target_language === 'ar' ? 'rtl' : 'ltr'}>
                    {clause.translation}
                  </p>
                </div>
              </div>
            </article>;
          })}
        </div>
      </>}
    </div>}
  </>;
}
