import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { DashboardPage } from "./pages/DashboardPage";
import { AdvancedPage } from "./pages/AdvancedPage";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { PageTransition } from "./components/layout/PageTransition";

export type PageType = "dashboard" | "advanced";

export function App() {
  const [currentPage, setCurrentPage] = useState<PageType>("dashboard");

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            {currentPage === "dashboard" ? (
              <PageTransition key="dashboard">
                <DashboardPage />
              </PageTransition>
            ) : (
              <PageTransition key="advanced">
                <AdvancedPage />
              </PageTransition>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

