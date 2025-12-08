import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Outlet } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Toaster } from "sonner";
import { DashboardPage } from "./pages/DashboardPage";
import { AdvancedPage } from "./pages/AdvancedPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { PageTransition } from "./components/layout/PageTransition";
import { AuthProvider, useAuth } from "./context/AuthContext";

export type PageType = "dashboard" | "advanced";

function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [currentPage, setCurrentPage] = useState<PageType>("dashboard");

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Carregando...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <Sidebar currentPage={currentPage} onNavigate={(page) => {
        setCurrentPage(page);
        // Manual routing via state for now inside dashboard, or could use real routes
      }} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
             {/* We can use Routes here or keep the manual state for the inner dashboard nav 
                 Let's use Routes for cleaner URL structure eventually, but for now, 
                 we need to map the Sidebar clicks to routes or keep state.
                 
                 Given Sidebar uses `onNavigate`, let's map routes to it.
             */}
             <Outlet />
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function DashboardWrapper() {
    // Wrapper to handle the internal "page" state of the existing Sidebar/Dashboard structure
    // if we want to keep the Sidebar component as is.
    // Ideally, Sidebar should use Link or navigate().
    // For this MVP step, let's adapt the existing "currentPage" logic to Routes.
    
    const { isAuthenticated } = useAuth();
    const [currentPage, setCurrentPage] = useState<PageType>("dashboard");

    // If we are authenticated, we show the layout
    if (!isAuthenticated) return <Navigate to="/login" replace />;

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

export function App() {
  return (
    <AuthProvider>
      <Router>
        <Toaster richColors position="top-right" />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          
          {/* Protected Route */}
          <Route path="/dashboard" element={<DashboardWrapper />} />
          
          {/* Redirect root to dashboard (which checks auth) */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
