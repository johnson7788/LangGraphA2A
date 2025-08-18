import React, { useState } from 'react';
//显示每个数据库的搜索结果的组件

const ResearchDisplay = ({ data }) => {
  console.log("要显示的搜索数据:", data)
  const [activeTab, setActiveTab] = useState(0); // State to manage the active tab


  // Assuming each item in toolResults.data represents a different tab/library
  const tabs = data.map((item) => ({
    name: item.name,
    data: item.data, // Assuming 'data' holds the list of research papers
  }));

  return (
    <div className="font-sans border border-gray-200 rounded-lg overflow-hidden shadow-md bg-white w-full max-w-lg mx-auto">
      <div className="flex border-b border-gray-200 bg-gray-50">
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`
              px-5 py-3
              text-base font-medium
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
        {tabs[activeTab] && tabs[activeTab].data.length > 0 ? (
          <ul>
            {tabs[activeTab].data.map((item, index) => (
              <li key={index} className="mb-2 last:mb-0">
                <a href={`${item.url}`} className="text-blue-600 hover:underline text-base">
                  {item.title}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500">No papers found in this library.</p>
        )}
      </div>
    </div>
  );
};

export default ResearchDisplay;