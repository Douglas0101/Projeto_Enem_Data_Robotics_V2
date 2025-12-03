import { Box, Flex, Text, BoxProps } from "@chakra-ui/react";
import { forwardRef } from "react";
import { cn } from "../../lib/utils";

// Adapter Component: Combines Chakra's Layout Props with Shadcn's Visual Style (Tailwind)

export const DashboardCard = forwardRef<HTMLDivElement, BoxProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <Box
        ref={ref}
        className={cn(
          "rounded-xl border bg-card text-card-foreground shadow-sm transition-all duration-300 hover:shadow-lg hover:-translate-y-1",
          className
        )}
        // Chakra props passed via ...props will override style if needed (e.g. w="100%")
        {...props}
      >
        {children}
      </Box>
    );
  }
);
DashboardCard.displayName = "DashboardCard";

export const DashboardCardHeader = ({ children, className, ...props }: BoxProps) => (
  <Flex
    // Default Shadcn Header style: flex-col, p-6. 
    // But we keep Chakra Flex to allow overrides via props (flexDir, align)
    direction="column"
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  >
    {children}
  </Flex>
);

export const DashboardCardTitle = ({ children, className, ...props }: BoxProps) => (
  <Text
    as="h3"
    className={cn(
      "text-xl font-semibold leading-none tracking-tight", 
      className
    )}
    {...props}
  >
    {children}
  </Text>
);

export const DashboardCardContent = ({ children, className, ...props }: BoxProps) => (
  <Box 
    className={cn("p-6 pt-0", className)} 
    {...props}
  >
    {children}
  </Box>
);

export const DashboardCardFooter = ({ children, className, ...props }: BoxProps) => (
  <Flex
    align="center"
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  >
    {children}
  </Flex>
);