import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/AppShell'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AuthProvider } from '@/context/AuthContext'
import { ForgotPasswordPage, LoginPage, RegisterPage, ResetPasswordPage } from '@/pages/AuthPages'
import {
  CategoriesPage,
  CategoryPage,
  HomePage,
  NotFoundPage,
  OfficialGuidePage,
  PublicAuthorPage,
  SearchResultsPage,
} from '@/pages/BrowsePages'
import { CreatePostPage, EditPostPage, PostDetailPage } from '@/pages/PostPages'
import {
  ChangePasswordPage,
  EditProfilePage,
  MyFavoritesPage,
  MyLikesPage,
  MyPostsPage,
  ProfilePage,
} from '@/pages/ProfilePages'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/categories/:slug" element={<CategoryPage />} />
            <Route path="/search" element={<SearchResultsPage />} />
            <Route path="/official-guide" element={<OfficialGuidePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/posts/:postId" element={<PostDetailPage />} />
            <Route path="/users/:userId" element={<PublicAuthorPage />} />
            <Route
              path="/create-post"
              element={
                <ProtectedRoute>
                  <CreatePostPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/posts/:postId/edit"
              element={
                <ProtectedRoute>
                  <EditPostPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/posts"
              element={
                <ProtectedRoute>
                  <MyPostsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/favorites"
              element={
                <ProtectedRoute>
                  <MyFavoritesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/likes"
              element={
                <ProtectedRoute>
                  <MyLikesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/edit"
              element={
                <ProtectedRoute>
                  <EditProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/change-password"
              element={
                <ProtectedRoute>
                  <ChangePasswordPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AppShell>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App

