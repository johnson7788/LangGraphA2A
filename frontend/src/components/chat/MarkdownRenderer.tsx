import React, { useState, useMemo, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

// Based on the structure from reference.md and References.tsx
interface MatchSentence {
    id: string;
    sentence: string;
    prefix_sentence: string;
    tail_sentence: string;
    db_id: number;
}

interface Reference {
  id: number;
  title: string;
  url?: string;
  match_sentence: string;
  match_sentences: MatchSentence[];
}

interface ReferenceSource {
  name: string;
  data: Reference[];
}

const HighlightMatch = ({ title, sentence, prefix_sentence, tail_sentence }: { title: string, sentence: string, prefix_sentence: string, tail_sentence: string }) => {
  return (
    <div className="p-2">
      <h3 className="text-base font-semibold mb-2">{title}</h3>
      <p className="text-sm">
        {prefix_sentence}
        <strong className="text-blue-600">{sentence}</strong>
        {tail_sentence}
      </p>
    </div>
  );
};

interface MarkdownRendererProps {
  content: string;
  references: ReferenceSource[];
  streaming: boolean;
}

interface ReferenceForMap extends MatchSentence {
    title: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, references, streaming }) => {
  const [activeRef, setActiveRef] = useState<{id: string, data: ReferenceForMap} | null>(null);
  const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const referenceMap = useMemo(() => {
    if (!references) return {};
    
    const flatRefs: ReferenceForMap[] = [];
    references.forEach(source => {
        source.data.forEach(ref => {
            if (ref.match_sentences) {
                ref.match_sentences.forEach(match => {
                    flatRefs.push({ ...match, title: ref.title });
                });
            }
        });
    });

    return flatRefs.reduce((acc, ref) => {
      acc[ref.id] = ref;
      return acc;
    }, {} as Record<string, ReferenceForMap>);
  }, [references]);

  const preprocessMarkdownWithRefs = (input: string) => {
    return input.replace(/\[\^([^\]]+)\]/g, (_, id: string) => {
      if (!referenceMap[id]) return `[^${id}]`;
      return `<sup data-ref-id="${id}" class="ref-link text-blue-600 cursor-pointer font-medium">[${id}]</sup>`;
    });
  };

  const handleMouseOver = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.dataset.refId) {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
        hideTimeoutRef.current = null;
      }
      const refId = target.dataset.refId;
      if (referenceMap[refId]) {
        setActiveRef({ id: refId, data: referenceMap[refId] });
        setPopupPosition({ top: e.clientY + 10, left: e.clientX + 10 });
      }
    }
  };
  
  const handleMouseOut = () => {
    hideTimeoutRef.current = setTimeout(() => {
      setActiveRef(null);
    }, 200);
  };

  const processedContent = preprocessMarkdownWithRefs(content);

  return (
    <div className="prose max-w-none text-gray-800 leading-relaxed relative" onMouseOver={handleMouseOver} onMouseOut={handleMouseOut}> 
        <ReactMarkdown
          children={processedContent}
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
          components={{
            p: ({ node, ...props }) => <p className="mb-4" {...props} />,
          }}
        />
        {streaming && (
            <span className="inline-block w-1 h-4 bg-blue-500 ml-1 animate-pulse" />
        )}

      {activeRef && (
        <div 
          data-popup="true" 
          className="fixed z-10 w-full max-w-md bg-white border border-gray-200 p-3 rounded-lg shadow-lg"
          style={{ top: popupPosition.top, left: popupPosition.left }}
          onMouseEnter={() => {
            if (hideTimeoutRef.current) {
              clearTimeout(hideTimeoutRef.current);
              hideTimeoutRef.current = null;
            }
          }}
          onMouseLeave={handleMouseOut}
        >
          <div className="flex justify-between items-center mb-2">
            <h4 className="font-bold text-base">Reference [{activeRef.id}]</h4>
          </div>
          <div className="max-h-48 overflow-y-auto text-sm">
            <HighlightMatch {...activeRef.data} />
          </div>
        </div>
      )}
    </div>
  );
};
