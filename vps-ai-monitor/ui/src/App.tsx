
import { useState } from "react";
import "./App.css";
import MonitoringConsole from "./MonitoringConsole";
import ContainersPage from "./ContainersPage";

type Tab = "monitor" | "containers";

export default function App() {
  const [tab, setTab] = useState<Tab>("monitor");

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
            VPS AI Monitor
          </h1>
          <nav className="flex gap-2">
            <button
              onClick={() => setTab("monitor")}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                tab === "monitor"
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Monitoring
            </button>
            <button
              onClick={() => setTab("containers")}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                tab === "containers"
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Conteneurs
            </button>
          </nav>
        </div>
      </header>

      <main className="py-6">
        {tab === "monitor" ? <MonitoringConsole /> : <ContainersPage />}
      </main>
    </div>
  );
}

