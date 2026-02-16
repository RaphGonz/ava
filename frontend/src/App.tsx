import { useEffect } from "react";
import { useAuthStore } from "./store/authStore";
import AuthForm from "./components/Auth/AuthForm";
import ChatWindow from "./components/Chat/ChatWindow";
import OnboardingFlow from "./components/Onboarding/OnboardingFlow";

export default function App() {
  const { isAuthenticated, fetchUser, user } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser();
    }
  }, [isAuthenticated, fetchUser]);

  if (!isAuthenticated) {
    return <AuthForm />;
  }

  if (user && !user.is_onboarded) {
    return <OnboardingFlow />;
  }

  return <ChatWindow />;
}
