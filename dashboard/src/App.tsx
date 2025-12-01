import { useState } from "react";
import { DashboardPage } from "./pages/DashboardPage";
import { AdvancedPage } from "./pages/AdvancedPage";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";

export type PageType = "dashboard" | "advanced";

export function App() {
  const [currentPage, setCurrentPage] = useState<PageType>("dashboard");

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          {currentPage === "dashboard" ? <DashboardPage /> : <AdvancedPage />}
        </main>
      </div>
    </div>
  );
}

