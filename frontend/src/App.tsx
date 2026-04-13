import { Routes, Route, NavLink } from "react-router-dom";
import { Zap, Target, List } from "lucide-react";
import Signals from "./pages/Signals";
import Tracker from "./pages/Tracker";
import Scanner from "./pages/Scanner";

const navLinks = [
  { to: "/", label: "Signals", icon: Zap },
  { to: "/tracker", label: "Tracker", icon: Target },
  { to: "/scanner", label: "All Stocks", icon: List },
];

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-200">
      <header className="border-b border-gray-800 px-4 py-2 flex items-center gap-6">
        <span className="text-lg font-bold text-emerald-400">NASDAQ Halal</span>
        <nav className="flex gap-1">
          {navLinks.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded text-sm ${
                  isActive ? "bg-emerald-500/20 text-emerald-400" : "text-gray-400 hover:text-gray-200"
                }`
              }>
              <Icon size={14} /> {label}
            </NavLink>
          ))}
        </nav>
        <span className="ml-auto text-xs text-gray-500">Halal T+1 Trading</span>
      </header>
      <main className="max-w-7xl mx-auto p-4">
        <Routes>
          <Route path="/" element={<Signals />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/scanner" element={<Scanner />} />
        </Routes>
      </main>
    </div>
  );
}
