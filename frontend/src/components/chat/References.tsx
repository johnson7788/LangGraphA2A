
import React, { useState } from 'react';

interface Reference {
  id: number;
  title: string;
  url?: string;
  match_sentence: string;
}

interface ReferenceSource {
  name: string;
  data: Reference[];
}

interface ReferencesProps {
  references: ReferenceSource[];
}

const References: React.FC<ReferencesProps> = ({ references }) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!references || references.length === 0) {
    return null;
  }

  const tabs = references.map(refSource => ({
    name: refSource.name,
    data: refSource.data,
  }));

  return (
    <div className="font-sans border border-gray-200 rounded-lg overflow-hidden shadow-md bg-white w-full max-w-4xl mx-auto mt-4">
      <div className="flex border-b border-gray-200 bg-gray-50">
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`
              px-5 py-3
              text-sm font-medium
              focus:outline-none transition-colors duration-300
              ${activeTab === index
                ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:bg-gray-100'
              }
            `}
            onClick={() => setActiveTab(index)}
          >
            {tab.name}
          </button>
        ))}
      </div>

      <div className="p-5">
        {tabs[activeTab] && tabs[activeTab].data && tabs[activeTab].data.length > 0 ? (
          <ul className="space-y-4">
            {tabs[activeTab].data.map((item, index) => (
              <li key={item.id || index} className="border-b border-gray-200 pb-2">
                <a href={item.url || '#'} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-base font-semibold">
                  {item.title}
                </a>
                <p className="text-sm text-gray-700 mt-1 italic">
                  "{item.match_sentence}"
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500">No references found in this source.</p>
        )}
      </div>
    </div>
  );
};

export default References;
