// Execute the shipping HTTP implementation against a real local TLS server.
#include "libgamestream/http.h"
#include "libgamestream/errors.h"
#include <stdio.h>
const char *gs_error;
int main(int argc, char **argv) {
  if (argc != 3) return 2;
  // Deliberately ignore the init result, as upstream gs_init currently does.
  http_init(argv[1], 0);
  PHTTP_DATA response = http_create_data();
  int result = http_request(argv[2], response);
  if (result != GS_OK) fprintf(stderr, "HTTP refused: %s\n", gs_error ? gs_error : "initialization failed");
  http_free_data(response);
  return result == GS_OK ? 0 : 1;
}
