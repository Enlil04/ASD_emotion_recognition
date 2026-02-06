enum UserRole {
  individual, // Standard user (Child/Teen)
  guardian,     // Guardian/Parent therapist
}


UserRole mapBackendRoleToEnum(String role) {
  switch (role.toLowerCase()) {
    case 'parent':
    case 'therapist':
      return UserRole.guardian;
    default:
      return UserRole.individual;
  }
}