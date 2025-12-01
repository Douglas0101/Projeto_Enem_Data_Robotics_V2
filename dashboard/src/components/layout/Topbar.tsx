import { Bell, Settings, Slash } from "lucide-react";
import { Button } from "../ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";

export function Topbar() {
  return (
    <header className="sticky top-0 z-50 flex h-16 w-full shrink-0 items-center gap-2 border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex flex-1 items-center gap-2">
        <div className="flex items-center text-sm text-muted-foreground">
          <span className="font-medium text-foreground hover:text-primary cursor-pointer transition-colors">
            Analytics
          </span>
          <Slash className="mx-2 h-4 w-4 text-muted-foreground/50" />
          <span className="font-medium text-foreground">
            Dashboard Geral
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full">
                <Bell className="h-4 w-4 text-muted-foreground" />
                <span className="sr-only">Notificações</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Notificações</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <span className="sr-only">Configurações</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Configurações</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </header>
  );
}
