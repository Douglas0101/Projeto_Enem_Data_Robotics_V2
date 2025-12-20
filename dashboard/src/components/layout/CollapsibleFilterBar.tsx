import { motion, AnimatePresence } from "framer-motion";
import { ChevronUp } from "lucide-react";
import { useLayout } from "../../context/LayoutContext";
import { FilterBar } from "../FilterBar";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";

/**
 * CollapsibleFilterBar - Wrapper component that adds an animated
 * toggle arrow to hide/show the FilterBar for distraction-free
 * chart visualization.
 */
export function CollapsibleFilterBar() {
  const { isFilterBarCollapsed, toggleFilterBar } = useLayout();

  return (
    <div className="relative">
      {/* Animated FilterBar Container */}
      <AnimatePresence initial={false}>
        {!isFilterBarCollapsed && (
          <motion.div
            key="filterbar"
            initial={{ height: 0, opacity: 0 }}
            animate={{ 
              height: "auto", 
              opacity: 1,
              transition: {
                height: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 }
              }
            }}
            exit={{ 
              height: 0, 
              opacity: 0,
              transition: {
                height: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.15 }
              }
            }}
            className="overflow-hidden"
          >
            <FilterBar />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle Arrow Button - Always Visible */}
      <div className="flex justify-center">
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <motion.button
                onClick={toggleFilterBar}
                className={cn(
                  "group flex items-center justify-center",
                  "w-full max-w-[120px] h-6",
                  "bg-gradient-to-b from-muted/50 to-muted/80",
                  "hover:from-primary/10 hover:to-primary/20",
                  "border-x border-b rounded-b-xl",
                  "transition-colors duration-200",
                  "focus:outline-none focus:ring-2 focus:ring-primary/50"
                )}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <motion.div
                  animate={{ rotate: isFilterBarCollapsed ? 180 : 0 }}
                  transition={{ 
                    type: "spring", 
                    stiffness: 400, 
                    damping: 25 
                  }}
                >
                  <ChevronUp 
                    className={cn(
                      "h-4 w-4 text-muted-foreground",
                      "group-hover:text-primary",
                      "transition-colors duration-200"
                    )} 
                  />
                </motion.div>
              </motion.button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              {isFilterBarCollapsed ? "Mostrar filtros" : "Ocultar filtros"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Collapsed State Indicator */}
      <AnimatePresence>
        {isFilterBarCollapsed && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex justify-center py-1"
          >
            <span className="text-xs text-muted-foreground/60">
              Filtros ocultos
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
