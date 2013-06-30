//
// bait.c
//
// GPL License and Copyright Notice ============================================
//  This file is part of Wrye Bash.
//
//  Wrye Bash is free software: you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation, either version 3 of the License, or
//  (at your option) any later version.
//
//  Wrye Bash is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
//
//  Wrye Bash Copyright (C) 2011 Myk Taylor
//
// =============================================================================


#include <linux/unistd.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <inttypes.h>

int32_t get_thread_id(void)
{
    return (int32_t)syscall(__NR_gettid);
}
