import {
  Box,
  Flex,
  Icon,
  Text,
  VStack,
  useColorModeValue
} from "@chakra-ui/react";
import { FiBarChart2, FiDatabase } from "react-icons/fi";

export function Sidebar() {
  const bg = useColorModeValue("white", "gray.900");
  const border = useColorModeValue("gray.200", "gray.700");

  return (
    <Box
      as="nav"
      aria-label="Main navigation"
      w={{ base: "full", md: "260px" }}
      borderRightWidth="1px"
      borderRightColor={border}
      bg={bg}
      px={6}
      py={6}
    >
      <Flex mb={8} align="center" gap={3}>
        <Box
          w={8}
          h={8}
          borderRadius="xl"
          bgGradient="linear(to-br, brand.500, brand.300)"
        />
        <Box>
          <Text fontSize="sm" fontWeight="medium" color="gray.500">
            ENEM Data Robotics
          </Text>
          <Text fontSize="lg" fontWeight="semibold">
            Analytics
          </Text>
        </Box>
      </Flex>

      <VStack align="stretch" spacing={2}>
        <Flex
          align="center"
          gap={3}
          px={3}
          py={2}
          borderRadius="lg"
          bg="brand.50"
          color="brand.700"
          fontWeight="medium"
        >
          <Icon as={FiBarChart2} />
          <Text fontSize="sm">Dashboard de Notas</Text>
        </Flex>
        <Flex
          align="center"
          gap={3}
          px={3}
          py={2}
          borderRadius="lg"
          color="gray.500"
          fontSize="sm"
        >
          <Icon as={FiDatabase} />
          <Text>Camadas Silver/Gold</Text>
        </Flex>
      </VStack>
    </Box>
  );
}

