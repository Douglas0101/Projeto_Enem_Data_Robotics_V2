import {
  Avatar,
  Box,
  Flex,
  HStack,
  Icon,
  IconButton,
  Text,
  useColorModeValue
} from "@chakra-ui/react";
import { FiBell, FiSettings } from "react-icons/fi";

export function Topbar() {
  const bg = useColorModeValue("white", "gray.900");
  const border = useColorModeValue("gray.200", "gray.700");

  return (
    <Flex
      as="header"
      align="center"
      justify="space-between"
      px={6}
      py={4}
      borderBottomWidth="1px"
      borderBottomColor={border}
      bg={bg}
    >
      <Box>
        <Text fontSize="sm" color="gray.500">
          Painel principal
        </Text>
        <Text fontSize="xl" fontWeight="semibold">
          Dashboard ENEM – Notas e Geografia
        </Text>
      </Box>

      <HStack spacing={3}>
        <IconButton
          aria-label="Notificações"
          variant="ghost"
          icon={<Icon as={FiBell} />}
        />
        <IconButton
          aria-label="Configurações"
          variant="ghost"
          icon={<Icon as={FiSettings} />}
        />
        <Avatar size="sm" name="Data Robotics" />
      </HStack>
    </Flex>
  );
}

