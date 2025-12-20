import {
  PieChart,
  ChevronLeft,
  LayoutDashboard,
  Settings,
  LogOut,
  User,
  LineChart,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLayout } from "../../context/LayoutContext";
import { useAuth } from "../../context/AuthContext";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { PageType } from "../../App";
import { motion, AnimatePresence } from "framer-motion";

interface NavItemProps {
  icon: React.ElementType;
  label: string;
  isActive?: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

const NavItem = ({ icon: Icon, label, isActive, isCollapsed, onClick }: NavItemProps) => {
  const content = (
    <motion.div
      onClick={onClick}
      className={cn(
        "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-accent-foreground cursor-pointer",
        isActive ? "text-accent-foreground" : "text-muted-foreground hover:bg-accent/50",
        isCollapsed && "justify-center px-2"
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      variants={{
        hidden: { opacity: 0, x: -10 },
        visible: { opacity: 1, x: 0 }
      }}
    >
      {isActive && (
        <motion.div
          layoutId="activeNav"
          className="absolute inset-0 bg-accent rounded-md"
          initial={false}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
          style={{ zIndex: -1 }}
        />
      )}
      <Icon className="h-4 w-4 z-10" />
      <AnimatePresence mode="wait">
        {!isCollapsed && (
          <motion.span 
            className="z-10"
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.2 }}
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
    </motion.div>
  );

  if (isCollapsed) {
    return (
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>{content}</TooltipTrigger>
          <TooltipContent side="right" className="flex items-center gap-4">
            {label}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return content;
};

interface SidebarProps {
  currentPage: PageType;
  onNavigate: (page: PageType) => void;
}

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const { isSidebarCollapsed, toggleSidebar } = useLayout();
  const { logout } = useAuth();

  return (
    <motion.aside
      className="group/sidebar relative flex h-full flex-col border-r bg-background"
      initial={false}
      animate={{ 
        width: isSidebarCollapsed ? 70 : 260 
      }}
      transition={{ 
        type: "spring", 
        stiffness: 300, 
        damping: 30 
      }}
    >
      {/* Premium Toggle Button - Always Visible */}
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <motion.button
              onClick={toggleSidebar}
              className={cn(
                "absolute -right-3 top-7 z-20",
                "flex h-6 w-6 items-center justify-center",
                "rounded-full border bg-background shadow-md",
                "hover:bg-primary hover:text-primary-foreground",
                "hover:shadow-lg hover:scale-110",
                "focus:outline-none focus:ring-2 focus:ring-primary/50",
                "transition-all duration-200"
              )}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <motion.div
                animate={{ rotate: isSidebarCollapsed ? 180 : 0 }}
                transition={{ 
                  type: "spring", 
                  stiffness: 400, 
                  damping: 25 
                }}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </motion.div>
            </motion.button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {isSidebarCollapsed ? "Expandir menu" : "Recolher menu"}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Header with Logo */}
      <div className={cn(
        "flex items-center gap-3 px-6 py-6 overflow-hidden",
        isSidebarCollapsed && "justify-center px-2"
      )}>
        <motion.div 
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-sm"
          whileHover={{ scale: 1.05, rotate: 5 }}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
        >
          <PieChart className="h-5 w-5" />
        </motion.div>
        <AnimatePresence mode="wait">
          {!isSidebarCollapsed && (
            <motion.div 
              className="overflow-hidden"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2, delay: 0.1 }}
            >
              <h1 className="text-sm font-bold tracking-tight whitespace-nowrap bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
                ENEM Data Robotics
              </h1>
              <p className="text-xs text-muted-foreground whitespace-nowrap">v2.0.1 Enterprise</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav Items */}
      <div className="flex-1 space-y-6 px-3 py-2">
        <div>
          <AnimatePresence mode="wait">
            {!isSidebarCollapsed && (
              <motion.h4 
                className="mb-2 px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                Analytics
              </motion.h4>
            )}
          </AnimatePresence>
          <motion.div 
            className="space-y-1"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {
                transition: {
                  staggerChildren: 0.1
                }
              }
            }}
          >
            <NavItem
              icon={LayoutDashboard}
              label="Dashboard Geral"
              isActive={currentPage === "dashboard"}
              isCollapsed={isSidebarCollapsed}
              onClick={() => onNavigate("dashboard")}
            />
            <NavItem
              icon={LineChart}
              label="Explorador Avançado"
              isActive={currentPage === "advanced"}
              isCollapsed={isSidebarCollapsed}
              onClick={() => onNavigate("advanced")}
            />
          </motion.div>
        </div>
      </div>


      {/* Footer User */}
      <div className="border-t p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <motion.div
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-md p-2 hover:bg-accent transition-colors",
                isSidebarCollapsed && "justify-center"
              )}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Avatar className="h-8 w-8 rounded-lg ring-2 ring-transparent hover:ring-primary/20 transition-all">
                <AvatarImage src="" />
                <AvatarFallback className="rounded-lg bg-gradient-to-br from-primary/20 to-primary/10 text-primary font-bold">
                  AU
                </AvatarFallback>
              </Avatar>
              <AnimatePresence mode="wait">
                {!isSidebarCollapsed && (
                  <motion.div 
                    className="flex flex-1 flex-col overflow-hidden text-left"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    <span className="truncate text-sm font-medium">Admin User</span>
                    <span className="truncate text-xs text-muted-foreground">
                      Data Scientist
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" side="right">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">Admin User</p>
                <p className="text-xs leading-none text-muted-foreground">
                  admin@datarobotics.com.br
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer">
              <User className="mr-2 h-4 w-4" />
              Perfil
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">
              <Settings className="mr-2 h-4 w-4" />
              Configurações
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              className="text-red-600 focus:bg-red-50 focus:text-red-600 cursor-pointer"
              onClick={logout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.aside>
  );
}