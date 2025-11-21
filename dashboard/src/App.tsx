import { Box, Flex } from "@chakra-ui/react";
import { DashboardPage } from "./pages/DashboardPage";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";

export function App() {
  return (
    <Flex minH="100vh">
      <Sidebar />
      <Box flex="1" display="flex" flexDirection="column">
        <Topbar />
        <Box as="main" flex="1" px={6} py={6}>
          <DashboardPage />
        </Box>
      </Box>
    </Flex>
  );
}

