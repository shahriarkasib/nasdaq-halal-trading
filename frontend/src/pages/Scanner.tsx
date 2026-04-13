import { useState } from "react";
import { List, Search, Shield } from "lucide-react";

export default function Scanner() {
  const [search, setSearch] = useState("");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <List className="text-purple-400" size={20} />
        <h1 className="text-xl font-bold">All Halal Stocks</h1>
        <span className="text-xs text-gray-500 ml-auto">
          <Shield size={12} className="inline text-emerald-400 mr-1" />
          Only showing Shariah-compliant stocks
        </span>
      </div>

      <div className="flex gap-3 items-center">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-2.5 text-gray-500" />
          <input
            type="text"
            placeholder="Search symbol or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <span className="text-xs text-gray-500">
          Halal screening: No banks, insurance, alcohol, gambling, weapons | Debt/MCap &lt; 33%
        </span>
      </div>

      <div className="p-8 text-center text-gray-500">
        <p>Full stock scanner coming soon.</p>
        <p className="text-xs mt-2">Will show all 1,800+ halal stocks with fundamentals, technicals, and signals.</p>
        <p className="text-xs mt-1">For now, check the Signals tab for today's buy recommendations.</p>
      </div>
    </div>
  );
}
