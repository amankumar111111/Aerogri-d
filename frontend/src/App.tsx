import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import CitizenFlow from "./pages/CitizenFlow";
import Dashboard from "./pages/Dashboard";
import SignalDetail from "./pages/SignalDetail";
import Analytics from "./pages/Analytics";
import Admin from "./pages/Admin";

function Nav() {
  const link = "px-3 py-2 text-sm font-medium rounded transition-colors";
  const active = "bg-emerald-700 text-white";
  const inactive = "text-gray-300 hover:bg-gray-700 hover:text-white";

  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-4 flex items-center h-14">
      <span className="text-emerald-400 font-bold text-lg mr-8">AEROGRID</span>
      <div className="flex gap-1">
        <NavLink to="/" className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          Report
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          Dashboard
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          Analytics
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          Admin
        </NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <Nav />
        <main className="max-w-7xl mx-auto p-4">
          <Routes>
            <Route path="/" element={<CitizenFlow />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/signals/:id" element={<SignalDetail />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
