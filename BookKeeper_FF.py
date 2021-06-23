
from math import copysign, isclose
from numpy import sign

class BookKeeper:
    def __init__(self, init_balance, transaction_fee=0, slippage={'type':'mult','value':0}):
        # print('fuck')
        self.balance=init_balance
        self.transaction_fee = transaction_fee
        self.slippage_input = slippage

        if slippage['type'] == 'mult':
            self.slippage = lambda: slippage['value']*self.current_price
        else:
             self.slippage = lambda: slippage['value']        
        
        self.current_position=0
        self.average_entry=0
        self.upnl=0
        self.current_price=0

        self.upnl_usd = 0
        self.balance_usd = 0

    def update_price(self, price, tv_er100=1):
        self.current_price=price
        self.upnl = self.pnl_calc(entry_price=self.average_entry, exit_price=self.current_price, contracts=self.current_position)
        self.upnl_usd = self.upnl*tv_er100
        return {
            'current_position':self.current_position,
            'average_entry':self.average_entry, 
            'upnl':self.upnl, 
            'upnl_usd':self.upnl_usd, 
            'balance': self.balance, 
            'balance_usd':self.balance_usd}

    def market_order(self, quantity, tv_er100=1):
        """NEW """
        # if quantity>0 then long, then slippage>0,
        # if quantity<0 then short, then slippage<0
        slippage = self.slippage()*copysign(1,quantity)
        executing_price = self.current_price+slippage 

        if (self.current_position<=0 and quantity<0) or (self.current_position>=0 and quantity>0):
            # print('INCREASING POSITION BY {}'.format(quantity))
            # ADDING TO POSITION:
            # reduces pnl! -- no only reduces for inverse perp swap

            self.average_entry = self.compute_new_average_entry(
                old_entry_price=self.average_entry, 
                old_contracts=self.current_position, 
                new_entry_price=executing_price, 
                new_contracts=quantity)                

            self.current_position += quantity

            self.upnl = self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=self.current_position)
            self.upnl_usd = self.upnl*tv_er100
            self.balance-=self.transaction_fee*abs(quantity)

        elif (self.current_position<0 and quantity>0) or (self.current_position>0 and quantity<0):
            # print('REDUCING POSITION BY {}'.format(quantity))
            # UPDATE upnl, and balance 

            if abs(quantity)>abs(self.current_position):
                # print('reversing')
                """ i.e.reversing position """
                self.upnl = 0 
                self.upnl_usd = 0
                pnl_pt = self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=self.current_position)
                self.balance += pnl_pt
                # self.balance -= self.transaction_fee*abs(quantity)

                self.balance_usd += pnl_pt*tv_er100

                self.current_position = sign(quantity)*abs(abs(quantity)-abs(self.current_position))
                self.average_entry  = executing_price


                # self.upnl = 0 
                # self.balance += self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=self.current_position)
                # self.balance -= self.transaction_fee*abs(quantity)
                # self.current_position = sign(quantity)*abs(abs(quantity)-abs(self.current_position))
                # self.average_entry  = executing_price



            elif abs(quantity)==abs(self.current_position): 
                """ i.e.exiting position """
                # note: the negative sign is because we are reducing position  
                self.upnl = 0 
                self.upnl_usd = 0
                pnl_pt = self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=self.current_position)
                self.balance += pnl_pt
                self.balance_usd += pnl_pt*tv_er100
                self.current_position = 0                
                self.average_entry =0

                # self.upnl = 0 
                # self.balance += self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=self.current_position)
                # self.current_position = 0                
                # self.average_entry =0                

            else: 
                """i.e. reducing position"""
                ## REDUCING but not exiting or reversing
                pnl = -self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=quantity)
                self.balance += pnl
                self.balance_usd += pnl*tv_er100
                self.upnl -= pnl
                self.current_position += quantity

                # pnl = -self.pnl_calc(entry_price=self.average_entry, exit_price=executing_price, contracts=quantity)
                # self.balance += pnl
                # self.upnl -= pnl
                # self.current_position += quantity                

        # self.balance=self.balance-self.transaction_fee*abs(quantity)

        return {'status':'FILLED', 'fill_price':self.current_price, 'submitted_quantity':quantity, 'executed_qty':quantity}
      

    def get_details(self):
        return {
            'current_position':self.current_position,
            'average_entry':self.average_entry, 
            'upnl':self.upnl, 
            'upnl_usd':self.upnl_usd, 
            'balance':self.balance, 
            'balance_usd':self.balance_usd}

    # def get_balance(self):
    #     return self.balance        

    @staticmethod     
    def compute_new_average_entry(old_entry_price, old_contracts, new_entry_price, new_contracts):
        # print(f"old_contracts:{old_contracts}")
        # print(f"new_contracts:{new_contracts}")
        # print(f"new_contracts+old_contracts:{new_contracts+old_contracts}")
        if isclose(new_contracts+old_contracts,0,abs_tol=1e-18):
            print('here')
            average_entry = 0
        # if you are short/long and the new_contracts is long/short, then you are 
        # reducing position, and your average entry price does not change
        elif (old_contracts<0 and new_contracts>0) or (old_contracts>0 and new_contracts<0) :
            average_entry = old_entry_price
        else: 
            average_entry = ((abs(old_contracts) * old_entry_price) +
                              (new_entry_price * abs(new_contracts))) / (abs(old_contracts)+abs(new_contracts)) 
        return average_entry
        
    # profit/loss calculator
    @staticmethod
    def pnl_calc(entry_price, exit_price, contracts):
        return (exit_price-entry_price)*contracts


