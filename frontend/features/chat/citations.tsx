import type { SourceCitation } from '@/lib/types';

// --- Types ---

type CitationGroup = {
  id: string;
  label: string;
  pageNumber?: number;
  count: number;
};

// --- Helpers ---

/** Groups raw citations by document ID to display consolidated badges. */
function groupCitations(sources: SourceCitation[]): CitationGroup[] {
  const groups = new Map<string, CitationGroup>();

  for (const source of sources) {
    const label = source.original_file_name?.trim() || 'Document';
    const key = source.document_id || label;
    const existing = groups.get(key);

    if (existing) {
      existing.count += 1;
    } else {
      groups.set(key, {
        id: key,
        label,
        pageNumber: typeof source.page_number === 'number' ? source.page_number : undefined,
        count: 1,
      });
    }
  }

  return [...groups.values()];
}

// --- Component ---

export function Citations({ sources }: { sources?: SourceCitation[] }) {
  // Early return if no sources exist
  if (!sources?.length) return null;

  return (
    <div className="flex flex-wrap gap-2 animate-in fade-in duration-300">
      {groupCitations(sources).map((citation) => (
        <span
          key={citation.id}
          className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs text-neutral-600 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
        >
          {/* Added title attribute for better UX on truncated text */}
          <span className="max-w-48 truncate" title={citation.label}>
            {citation.label}
          </span>

          {typeof citation.pageNumber === 'number' && <span>p.{citation.pageNumber}</span>}

          {citation.count > 1 && <span>×{citation.count}</span>}
        </span>
      ))}
    </div>
  );
}
