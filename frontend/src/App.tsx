import { useEffect } from "react";
import { useAuthStore } from "./store/authStore";
import AuthForm from "./components/Auth/AuthForm";
import ChatWindow from "./components/Chat/ChatWindow";

export default function App() {
  const { isAuthenticated, fetchUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser();
    }
  }, [isAuthenticated, fetchUser]);

  if (!isAuthenticated) {
    return <AuthForm />;
  }

  return <ChatWindow />;
}
