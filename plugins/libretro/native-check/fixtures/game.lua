-- Original Korri native runner fixture. SPDX-License-Identifier: CC0-1.0
local first=true
function TIC()
 if first then pmem(0,pmem(0)+1) first=false end
 cls(3)
 rect(20,20,40,40,6)
 if btn(0) then pix(0,0,12) end
end
