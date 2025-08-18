import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw'; // 支持 HTML 标签

const trimText = (text, length, position = 'end') => {
  if (text.length <= length) return text;
  return position === 'start'
    ? '...' + text.slice(-length)
    : text.slice(0, length) + '...';
};

// 定义一个HighlightMatch组件，接收title、sentence、prefix_sentence、tail_sentence四个参数
const HighlightMatch = ({ title, sentence, prefix_sentence,tail_sentence }) => {

  // 返回一个div，包含一个h2标题和p段落
  return (
    <div className="p-4">
      <h2 className="text-xl font-semibold mb-2">标题:{title}</h2>
      <p>
        {prefix_sentence}
        <strong className="font-bold">{sentence}</strong>
        {tail_sentence}
      </p>
    </div>
  );
};

export default function MessageRenderer({ text, referenceMap }) {
  const [activeRef, setActiveRef] = useState(null);

  const preprocessMarkdownWithRefs = (input) => {
    return input.replace(/\[\^([^\]]+)\]/g, (_, id) => {
      if (!referenceMap[id]) return `[^${id}]`;
      return `<sup data-ref-id="${id}" class="ref-link text-blue-600 cursor-pointer underline underline-offset-2">[${id}]</sup>`;
    });
  };

  const handleClick = (e) => {
    const refId = e.target.dataset.refId;
    if (refId && referenceMap[refId]) {
      setActiveRef({ id: refId, data: referenceMap[refId] });
    }
  };

  const processedText = preprocessMarkdownWithRefs(text);

  return (
    <div className="relative">
      <div onClick={handleClick}>
        <ReactMarkdown
          children={processedText}
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
          components={{
            p: ({ node, ...props }) => <p className="text-lg leading-relaxed" {...props} />,
          }}
        />
      </div>

      {activeRef && (
        <div className="absolute z-50 bg-white border p-4 rounded shadow-lg max-w-md">
          <h4 className="font-bold mb-2">引用 [{activeRef.id}]</h4>
          <div className="max-w-3xl mx-auto">
            <HighlightMatch {...activeRef.data} />
          </div>
          <button
            className="mt-2 text-blue-600 underline"
            onClick={() => setActiveRef(null)}
          >
            关闭
          </button>
        </div>
      )}
    </div>
  );
}
