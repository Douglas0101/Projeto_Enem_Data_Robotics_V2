import {
  BarChart2,
  PieChart,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Settings,
  LogOut,
  User,
  LineChart,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLayout } from "../../context/LayoutContext";
import { Button } from "../ui/button";
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

interface NavItemProps {
  icon: React.ElementType;
  label: string;
  isActive?: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

const NavItem = ({ icon: Icon, label, isActive, isCollapsed, onClick }: NavItemProps) => {
  const content = (
    <div
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer",
        isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground",
        isCollapsed && "justify-center px-2"
      )}
    >
      <Icon className="h-4 w-4" />
      {!isCollapsed && <span>{label}</span>}
    </div>
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

  return (
    <aside
      className={cn(
        "group/sidebar flex h-full flex-col border-r bg-background transition-all duration-300 ease-in-out",
        isSidebarCollapsed ? "w-[70px]" : "w-[260px]"
      )}
    >
      {/* Toggle Button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute -right-3 top-6 z-20 h-6 w-6 rounded-full border bg-background shadow-sm hover:bg-accent hidden group-hover/sidebar:flex"
        onClick={toggleSidebar}
      >
        {isSidebarCollapsed ? (
          <ChevronRight className="h-3 w-3" />
        ) : (
          <ChevronLeft className="h-3 w-3" />
        )}
      </Button>

      {/* Header */}
      <div className={cn("flex items-center gap-3 px-6 py-6", isSidebarCollapsed && "justify-center px-2")}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <PieChart className="h-5 w-5" />
        </div>
        {!isSidebarCollapsed && (
          <div className="overflow-hidden transition-all">
            <h1 className="text-sm font-bold tracking-tight whitespace-nowrap">ENEM Data Robotics</h1>
            <p className="text-xs text-muted-foreground whitespace-nowrap">v2.0.1 Enterprise</p>
          </div>
        )}
      </div>

      {/* Nav Items */}
      <div className="flex-1 space-y-6 px-3 py-2">
        <div>
          {!isSidebarCollapsed && (
            <h4 className="mb-2 px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Analytics
            </h4>
          )}
          <div className="space-y-1">
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
          </div>
        </div>
      </div>


      {/* Footer User */}
      <div className="border-t p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-md p-2 hover:bg-accent transition-colors",
                isSidebarCollapsed && "justify-center"
              )}
            >
              <Avatar className="h-8 w-8 rounded-lg">
                <AvatarImage src="" />
                <AvatarFallback className="rounded-lg bg-primary/10 text-primary font-bold">AU</AvatarFallback>
              </Avatar>
              {!isSidebarCollapsed && (
                <div className="flex flex-1 flex-col overflow-hidden text-left">
                  <span className="truncate text-sm font-medium">Admin User</span>
                  <span className="truncate text-xs text-muted-foreground">
                    Data Scientist
                  </span>
                </div>
              )}
            </div>
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
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Perfil
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Configurações
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-600 focus:bg-red-50 focus:text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}